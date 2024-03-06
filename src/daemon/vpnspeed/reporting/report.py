import os
import shutil
import pandas as pd
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import math
import zipfile
from dataclasses import dataclass
from datetime import datetime, date, timedelta
from functools import partial
from pandas import DataFrame, Series
from typing import List, Tuple, AsyncIterator
from vpnspeed import errors
from vpnspeed.datasink import DataBackup
from vpnspeed.model import *
from vpnspeed import log


_TITLE_TEXT_SIZE = 14
_AXIS_LABEL_TEXT_SIZE = 12


@dataclass
class ReportFilter:
    value: str = None
    end: date = None
    start: date = None
    outliers: float = 0.00

    def with_defaults(self):
        self.value = self.value or "download_speed"
        self.end = self.end or datetime.now().date()
        self.start = self.start or self.end - timedelta(days=7)
        return self

    @classmethod
    def default(cls):
        return cls().with_defaults()

    def validate(self):
        values = ["download_speed", "upload_speed"]
        if self.value not in values:
            raise errors.APIError(
                f"Incorrect 'value': '{self.value}', valid values: {values}."
            )
        if self.outliers < 0 or self.outliers > 1:
            raise errors.APIError(
                f"Incorrect 'outliers': '{self.outliers}', valid values ar beetween 0 and 1."
            )
        if self.start >= self.end:
            raise errors.APIError(
                f"Incorrect 'start'/'end' range, must satisfy 'start' < 'end'"
            )


@dataclass
class Report:
    averages: DataFrame = None
    average_over_time: DataFrame = None
    runs_by_hour: DataFrame = None
    percentiles: DataFrame = None


class ReportGenerator:
    _db: DataBackup

    def __init__(self, db: DataBackup):
        self._db = db

    async def make_plots(self, path, filter_=ReportFilter.default()) -> str:
        folder = datetime.utcnow().strftime("report.%Y%m%d%H%M%S")
        path = os.path.join(path, folder)
        os.makedirs(path, exist_ok=True)
        unique_identifier: str = ""

        try:
            zip_file = path + ".zip"

            with zipfile.ZipFile(zip_file, "w", zipfile.ZIP_DEFLATED) as zip_:
                async for group, report in self.make_reports(filter_):
                    if group.vpn_city is not None:
                        unique_identifier = "-" + group.vpn_city
                    group_name = (
                        group.vpn_country
                        + "-"
                        + group.target_country
                        + unique_identifier
                    )
                    # Plot averages
                    plot_path = self._plot_averages(
                        report.averages, filter_.value, group_name, path
                    )
                    zip_.write(
                        plot_path, os.path.join(folder, os.path.basename(plot_path))
                    )
                    # Plot average over time
                    plot_path = self._plot_average_over_time(
                        report.average_over_time, filter_.value, group_name, path
                    )
                    zip_.write(
                        plot_path, os.path.join(folder, os.path.basename(plot_path))
                    )
                    # Plot runs by hour
                    plot_path = self._plot_runs_by_hour(
                        report.runs_by_hour, group_name, path
                    )
                    zip_.write(
                        plot_path, os.path.join(folder, os.path.basename(plot_path))
                    )
                    # Plot percentiles
                    plot_path = self._plot_percentiles(
                        report.percentiles, filter_.value, group_name, path
                    )
                    zip_.write(
                        plot_path, os.path.join(folder, os.path.basename(plot_path))
                    )

            return zip_file

        finally:
            shutil.rmtree(path)

    async def make_reports(
        self, filter_=ReportFilter.default()
    ) -> AsyncIterator[Tuple[TestGroup, Report]]:
        groups = await self._db.retrieve_groups()
        unique_groups = {}
        unique_groups_df = {}
        for group in groups:
            if group.vpn_country != group.target_country:
                continue
            group_dataframe = await self._get_dataframe(group, filter_)
            if group_dataframe is None:
                continue
            if group.vpn_country in unique_groups:
                new_dataframe = DataFrame(
                    unique_groups_df[group.vpn_country].append(group_dataframe)
                )
                unique_groups_df[group.vpn_country] = new_dataframe
                continue
            unique_groups[group.vpn_country] = TestGroup(
                group.vpn_country,
                group.target_country,
                None,
                group.target_server,
                group.target_server_id,
            )
            unique_groups_df[group.vpn_country] = DataFrame(group_dataframe)
        for group_name in unique_groups_df:
            report = await self.make_report_from_dataframe(
                unique_groups_df[group_name], filter_
            )
            if report is not None:
                yield (unique_groups[group_name], report)

    async def make_report(
        self, group: TestGroup, filter_=ReportFilter.default()
    ) -> Report:
        df = await self._get_dataframe(group, filter_)
        if df is None:
            return None

        filtered_df = self._filter_outliers(df, filter_)
        return Report(
            averages=self._calculate_averages(filtered_df, filter_.value),
            average_over_time=self._calculate_average_over_time(
                filtered_df, filter_.value
            ),
            runs_by_hour=self._calculate_runs_by_hour(df),
            percentiles=self._calculate_percentiles(
                df, filter_.outliers, filter_.value
            ),
        )

    async def make_report_from_dataframe(
        self, df: DataFrame, filter_=ReportFilter.default()
    ) -> Report:
        filtered_df = self._filter_outliers(df, filter_)
        return Report(
            averages=self._calculate_averages(filtered_df, filter_.value),
            average_over_time=self._calculate_average_over_time(
                filtered_df, filter_.value
            ),
            runs_by_hour=self._calculate_runs_by_hour(df),
            percentiles=self._calculate_percentiles(
                df, filter_.outliers, filter_.value
            ),
        )

    async def _get_dataframe(
        self, group: TestGroup, filter_: ReportFilter
    ) -> DataFrame:
        filter_ = filter_.with_defaults()
        data = await self._db.retrieve(
            group=group, start=filter_.start, end=filter_.end
        )
        if len(data) == 0:
            return None
        df = DataFrame.from_records(data)

        def name_fix(name: str):
            if name.startswith("run_"):
                return name[4:]
            return name

        df = df.rename(columns=name_fix)

        df["group_vpn_country"] = df["group_vpn_country"].replace("uk", "gb")
        df["case_technology"] = df["case_technology"].replace("ipsec/ikev2", "ikev2")
        df["download_speed"] = df["download_bandwidth"] * 8 / 10 ** 6
        df["upload_speed"] = df["upload_bandwidth"] * 8 / 10 ** 6
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["date"] = df["timestamp"].dt.date
        df["hour"] = df["timestamp"].dt.hour
        df["megabytes_received"] = df["download_bytes"] / 10 ** 6
        if "case_vpn" in df and "case_technology" in df:
            df["case"] = df["case_vpn"] + "-" + df["case_technology"]
        if "case_protocol" in df:
            df["case"] += df["case_protocol"].apply(
                lambda x: "-" + x if not pd.isnull(x) else ""
            )

        return df

    def _filter_outliers(self, df: DataFrame, filter_: ReportFilter) -> DataFrame:
        # Remove outliers
        cases = df.groupby("case")
        df = DataFrame()
        for index in cases.indices:
            case = cases.get_group(index)
            min_value = case[filter_.value].quantile(filter_.outliers)
            max_value = case[filter_.value].quantile(1 - filter_.outliers)

            df = pd.concat(
                [
                    df,
                    pd.DataFrame(
                        case[
                            (case[filter_.value] > min_value)
                            & (case[filter_.value] < max_value)
                        ]
                    ),
                ]
            )
        return df

    def _calculate_averages(self, df: DataFrame, field: str) -> DataFrame:
        df = df[["case", field]]
        df = df.groupby("case").agg("mean")
        df = df.sort_values(by=[field])
        return df

    def _calculate_average_over_time(self, df: DataFrame, field: str) -> DataFrame:
        """Create [case x date] table with mean df"""
        df = df[["case", "date", field]]
        df = df.groupby(["case", "date"])[field].agg("mean").reset_index()
        df = df.pivot(index="date", columns="case", values=field).sort_index()
        return df

    def _calculate_runs_by_hour(self, df: DataFrame) -> DataFrame:
        """Create [hours x case] table with run count df"""
        df = df[["case", "hour", "timestamp"]]
        df = df.groupby(["case", "hour"])["timestamp"].count().reset_index(name="count")
        df = df.pivot_table(index="case", columns="hour", values="count", fill_value=0)
        for hour in range(24):
            if hour not in df:
                df[hour] = 0
        df = df[list(range(24))]
        return df

    def _calculate_percentiles(
        self, df: DataFrame, outliers: float, field: str
    ) -> DataFrame:
        """Create [precentile x case] table with field df"""

        def ordinal(p) -> str:
            if p == outliers:
                return "5th"
            if p == 1 - outliers:
                return "95th"
            p = int(p * 100)
            if p % 10 == 1:
                return str(p) + "st"
            if p % 10 == 2:
                return str(p) + "nd"
            if p % 10 == 3:
                return str(p) + "rd"
            return str(p) + "th"

        return (
            df.groupby("case")[field]
            .agg(
                [
                    (ordinal(q), partial(Series.quantile, q=q))
                    for q in [outliers, 0.25, 0.50, 0.75, 1 - outliers]
                ]
            )
            .sort_values(by=["50th"])
        )

    def _plot_averages(self, df: DataFrame, field: str, group: str, path: str) -> str:
        x_axis = df.index
        y_axis = df[field].round(2)

        plt.figure(figsize=(15, 8))
        plt.bar(x_axis, y_axis, align="center", yerr=None, capsize=5, color="lightgrey")

        plt.title("Average ({})".format(group), size=_TITLE_TEXT_SIZE)
        plt.xlabel("Provider & protocol", size=_AXIS_LABEL_TEXT_SIZE)
        plt.ylabel("Speed, Mbps", size=_AXIS_LABEL_TEXT_SIZE)
        plt.xticks(range(len(x_axis)), x_axis, rotation=7)

        for i in range(len(x_axis)):
            height = y_axis[i] / 2
            plt.text(
                x=x_axis[i],
                y=height - 0.1,
                s=y_axis[i],
                ha="center",
                size=_AXIS_LABEL_TEXT_SIZE,
            )

        plot_path = os.path.join(path, "bar_mean_{}_{}.png".format(field, group))
        plt.savefig(plot_path)
        plt.close()
        return plot_path

    def _plot_average_over_time(
        self, df: DataFrame, field: str, group: str, path: str
    ) -> str:
        _, ax = plt.subplots(figsize=(15, 8))
        plt.title("Average speed over time ({})".format(group), size=_TITLE_TEXT_SIZE)
        plt.xlabel("Date", size=_AXIS_LABEL_TEXT_SIZE)
        plt.ylabel("Speed, Mbps", size=_AXIS_LABEL_TEXT_SIZE)

        for case in df.columns:
            ax.plot(df[case])

        ax.xaxis.set_major_locator(mdates.DayLocator())

        plot_path = os.path.join(path, "line_mean_{}_{}.png".format(field, group))
        ax.legend(df.columns)
        plt.savefig(plot_path)
        plt.close()
        return plot_path

    def _plot_runs_by_hour(self, df: DataFrame, group: str, path: str) -> str:
        cols = min(3, len(df.index))
        rows = math.ceil(len(df.index) / cols)

        fig, axs = plt.subplots(rows, cols, figsize=(5 * cols, 5 * rows), sharey="row")
        if cols == 1:
            axs = [[axs]]
        elif rows == 1:
            axs = [axs]

        fig.suptitle("Test distribution per time, per case ({})".format(group))
        for i in range(len(df.index)):
            col = i % 3
            row = i // 3
            ax = axs[row][col]
            ax.bar(df.columns, df.iloc[i], edgecolor="grey", color="lightgrey")
            ax.set_ylabel("Number of times")
            ax.set_xlabel("Hour when the test performed")
            ax.set_title(df.index[i])

        plot_path = os.path.join(path, "bar_runs_{}.png".format(group))
        plt.savefig(plot_path)
        plt.close()
        return plot_path

    def _plot_percentiles(
        self, df: DataFrame, field: str, group: str, path: str
    ) -> str:
        stacked_df = DataFrame()

        cols = df.columns
        stacked_df[""] = df[cols[0]].round()
        for i in range(len(df.columns) - 1):
            stacked_df[cols[i] + "-" + cols[i + 1]] = (
                df[cols[i + 1]] - df[cols[i]]
            ).round()

        ax = stacked_df.plot(
            kind="bar",
            figsize=(15, 10),
            fontsize=13,
            width=0.8,
            edgecolor="#EBEDEF",
            legend=False,
            color=[
                "None",
                "lightblue",
                "lightsteelblue",
                "lightsteelblue",
                "lightblue",
            ],
            stacked=True,
        )

        formated_axis_name = "{} percentiles ({})".format(
            field.capitalize().replace("_", " "), group
        )

        ax.set_title(formated_axis_name, fontsize=_TITLE_TEXT_SIZE)
        ax.set_xlabel("Provider & protocol", fontsize=_AXIS_LABEL_TEXT_SIZE)
        ax.set_ylabel("Speed, Mbps", fontsize=_AXIS_LABEL_TEXT_SIZE)
        plt.xticks(rotation=15)

        # base_labels = ['', '5th-25th', '25th-50th', '50th-75th', '75th-95th']
        patches = ax.patches
        for i, patch in enumerate(ax.patches):
            label = stacked_df.columns[int(i / len(stacked_df.index))]
            if label == "":
                continue

            if patch.get_width() > 0:
                x = patch.get_x() + patch.get_width() / 2
                y = patch.get_y() + patch.get_height() / 2
                ax.text(x, y, label, ha="center", va="center", fontsize=10)

        plot_path = os.path.join(path, "percentiles_{}_{}.png".format(field, group))
        plt.savefig(plot_path)
        plt.close()
        return plot_path
