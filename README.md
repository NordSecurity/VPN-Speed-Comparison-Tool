# VPN Speed Comparison Tool

This is a tool, written in Python, for assessing network speed over VPN connections.

It is composed of two main parts: the daemon, which is invoked using the `vpnspeedd` command, and the client, which is invoked using the `vpnspeed` command. The daemon awaits instructions from the client and executes the given tests in the background. The client controls the test configuration and daemon life-cycle.

Detailed whitepaper with the methodology can be found here: https://nordvpn.com/vpn-speed-test/

### Dependencies:
```
apt-transport-https  
ca-certificates  
curl  
docker-ce  
docker-compose  
git  
gnupg  
jq  
python3-dev  
python3-pip  
python3-setuptools  
python3-wheel  
python3-yaml  
software-properties-common  
wireguard  
```
Notes:
* Test can be started by running `scripts/setup.sh`, which will install all dependencies.
* This project was build and mainly tested using **debian 10**, other distribution of debian can be incompatible. 

### IP geolocation
   For test execution ip geoservice is needed. In this project `ipapi.co` was selected.
   > Note: More information about pricing and limitations visit https://ipapi.co .

### Supported providers and technologies
<!--  -->
 * NordVPN (app)
    * OpenVPN (udp/tcp)
    * Nordlynx
 * ExpressVPN (app)
    * OpenVPN (udp)
    * Lightway
 * Surfshark
    * OpenVPN (udp)
    * IKEv2
    * Wireguard
 * Private Internet Access (app)
    * Openvpn (udp)
    * Wireguard
 * PureVPN (app)
    * OpenVPN (udp)
<!--  -->


### Supported data receivers
 * SQLite
    * also supported as a backup data sink (read more [here](#test-results))
 * CSV
    * also supported as a backup data sink (read more [here](#test-results))


### Supported speed tests
 * [Speedtest CLI](https://www.speedtest.net/apps/cli)


## Usage

1. First, clone the repository with the following command:
```sh
$ git clone https://github.com/NordSecurity/VPN-Speed-Comparison-Tool
```

2. After cloning the repository and before starting the testing process, edit the configuration file to add VPN provider credentials and further customize test execution.
```sh
$ vi vpnspeed.yaml
```

3. Run using `scripts/setup.sh`
```sh
$ sudo ./scripts/setup.sh
```
Note:
*  Adding `--dry-run` to `setup.sh` will only install, but not start test with configuration.
```sh
$ sudo scripts/setup.sh --dry-run`
```
### Local - manually

To run the tests locally, run the following commands in the project root. The following commands will start a docker container, start the `vpnspeedd` daemon on it and leave it running in the background:

```sh
$ cd ./docker
$ docker-compose up -d
```

To start the tests, run:

```sh
$ docker-compose exec runner vpnspeed up /opt/vpnspeed/vpnspeed.yaml
```

Find out more about the possible commands and usage by running:

```sh
$ docker-compose exec runner vpnspeed --help
```

Once you are done executing the tests and want to stop the container, use:

```sh
$ docker-compose down
```

### Remote (via ssh debian based system)

1. Configure `vpnspeed.yaml` - specify vpn credentials and testing countries

   > On configuration failure just stop and start probe with correct configuration using `vpnspeed stop` and `vpnpseed up <config>` command.

2. Run `install_to.sh` script localy to install vpnspeed to remote:

```sh
$ ./scripts/install_to.sh root@somehost
```

Notes: 
* You could manually copy this project to remote machine and run `./script/setup.sh`.  
* Probe daemon runs in a docker container build from `./docker/docker-compose.yml`  
* `./scripts/install_to.sh root@somehost --dry-run` will setup speedtest tool to host but will not start testing.  

3. Monitor machine:

```sh
$ ssh root@somehost

# vpnspeed context state | jq .      -> see if probe is running or idling

# vpnspeed context groups | jq .     -> see all TestGroups X TestCases status

# vpnspeed context groups[0] | jq .  -> see first TestGroup and it's Cases

# vpnspeed down                      -> stop probe

# vpnspeed up <config>               -> start probe with specified config

# vpnspeed data                      -> get collected data (CSV)

# vpnspeed data -f json              -> get collected data (JSON)

# vpnspeed report                    -> generate report.XXXX.zip with plots

# vpnspeed logs                      -> shows daemon executed test logs from `/var/log/vpnspeed/vpnspeed.log`

```

Reports can be filtered by: 
   - --start (-s) date - **default: NOW**, start date of runs (if only start is specified, **end** = **start** + 7d)
   - --end (-e) date - **default: NOW - 7d**, end date of runs (if only end is specified, **start** = **end** - 7d)
   - --value (-v) - **default: download_speed**, value to be aggregated and compared
   - --outliers (-o) - **default: 0.00**, specify what percentage of worst/best data to ignore
   
e.g.:
```sh
$ vpnspeed report -s YYYY-MM-DD -e YYYY-MM-DD -v value -o 0.03 <some directory>
```
Note:
   * If `<some directory>` param is not set, report will be generate in `report` volume.

## Configuration

The tests can be customized using a `yaml` configuration file. It can be used to specify the following parts of test execution:

| Argument | Description |
| ----- | ----------- |
| Interval | Describes how much time passes between each test run. |
| Run mode | Which run mode to use (read more [here](#test-execution)). |
| Run repeats | How many times each test is repeated when using run mode `once` (read more [here](#test-execution)). |
| VPN and target countries | Which countries the VPN should connect to and to which countries the test should run (read more [here](#about-the-data)). |
| VPN providers | VPN providers to use in the tests (see [list of supported providers](#supported-providers-and-technologies)). |
| VPN technologies | Which VPN technologies to use with a given VPN provider (see [list of supported providers](#supported-providers-and-technologies)). |
| Transport protocols | Which transport protocol to use for a given VPN technology. |
| Data sinks | Databases that test results should be sent to (see [list of supported data sinks](#supported-data-receivers)). |

More details and usage examples can be found in the [example configuration file](vpnspeed.yaml).

## Further documentation
### About the data
The speed test identifies three different locations:
* probe - this is the location from which the tests are executed. It is either your computer, if you run the tests locally, or the remote server;
* VPN country - the country that the VPN connects to;
* target country - to which country the speed test is performed.
By default, the VPN country is chosen by the VPN provider's reccommendation algorithm and the target country is chosen by the speed test tool (a server with lowest latency from the VPN server).

The testing data is roughly modeled as such:
* Config - machine configuration and all test parameters.
    * VPN - all information on the VPN providers that should be tested. This includes the selected providers, their respective credentials, technologies and protocols to be tested for each.
    * Test group - groups are generated by the service and are combinations of VPN country and target country.
        * Test case - cases are also generated by the service and are combinations of VPN provider, technology and protocol.
            * Test run - runs store the results of each test execution given the setup from test groups and test cases.

### Test execution
The flow of each test run is roughly as follows:
* the VPN connection is set up:
    * the provider is chosen using the test case;
    * a server to connect to is identified using the VPN country specified in the test group;
    * the actual connection is started using the technology and protocol specified in the test case;
* the speed test tool is run:
    * a target server is chosen based on the target country specified in the test group;
    * the test is executed;
* the test's results are saved in a test run.

The test runner executes the tests at an interval that can be specified in the config. It also identifies two test run modes:
* continuous (default) - tests are executed indefinitely, or until some unexpected exception occurs;
* once - each test group and test case combination gets run once and the testing ends.

Given the `continuous` mode, the runner selects a group-case pair by identifying a combination that has been run the least number of times for each run. This is to ensure that run distribution across group-case pairs is similar. Given the `once` mode, the runner simply iterates over all group-case pairs once. For this mode, it is also possible to specify how many times each test should be repeated in the config. This is to make the test data more reliable and error-proof.

Aside from run modes, there is one more feature related to test execution - the scheduler. It creates a cron job to start the testing at given times. The scheduler is used in combination with tests that use run mode `once`. The actual schedule can be specified in two ways - either by providing an interval in hours, or by providing a cron string to customize the schedule in more detail.


### Test results
All test results acquired are sent to any data sinks that are specified in the config. It is possible to define some data sinks as backup sinks. These should be sinks that are stored locally (for instace, a sqlite database) and they are used to retrieve data when needed.

After some {statistically significant amount of} data has been acquired, it is possible to generate some reports on it. The test results are retrieved from any backup data sinks and used to create a {percentile graph}. The data is grouped by {provider and technology}.

### VPNs
Currently there are two ways the tool connects to VPN - via the provider's app or by using the technologies natively. Check the [list of supported providers](#supported-providers-and-technologies) to see which ones can be used with an app.

To test with one of the supported VPN providers, you should have an account with them and provide your credentials in the configuration file.  
Credential is used same as corresponding app login `username` and `password`.
> Specifically for the ExpressVPN app you need to provide an activation key only as the `password` parameter.

Note:
* Please disable MFA login for configured providers, because it will fail vpn application login.

### Errors
There are three main types of errors that are handled in the tool:

| Error type | Causes | Handling |
| -- | -- | -- |
| Test group error | Could not find target servers to perform the speed test to. | The test group is marked as failed and is not executed further. |
| Test case error | The selected provider is not supported.<br/>The selected provider does not support the selected technology.<br/>The selected technology does not support the selected protocol.<br/>Failed to query the provider's API.<br/>Failed to authenticate with the given credentials. | The test case is marked as failed and is not executed further |
| Test run error | Failed to establish a VPN connection.<br/>Unexpected errors from the speed test tool. | The test case for this run is marked as failed. After three test run failures for one case, that case is not executed further. |

In order to not halt the testing process for long running tests (specifically, when using the `continuous` run mode), all fail marks are cleared after `groups * cases` number of runs to bring them back into iteration and try again.

## Configuration file
| Key | Explanation | Example |
| -- | -- | -- |
| `config` | Main key defines start of configuration | -- |
| `intervals` | Interval is the amount of time (in seconds) that is awaited before each test run |```interval: 180```|
| `mode` | This defines if all the combinations should run indefinitely (default value 'continuous'), or just once (value 'once') | ```mode: continuous```|
| `repeats` | Define the number of times a single test combination is executed. By default each combination is run only once. | ```repeats: 1```|
| `common_cities` | Find Common cities for specified test groups. By default common city search is executed. | ```common_cities: true``` |
| `groups` | Groups define the VPN and speed test target countries. The VPN country and target country can be provided in one of three ways. In case the VPN or target country is not relevant, specify 'auto' instead of a country code. | The short version is:<br />```groups:```<br />&nbsp;&nbsp;&nbsp;&nbsp;```- us:us```, <br />The long version looks as such:<br />```groups:```<br />&nbsp;&nbsp;&nbsp;&nbsp;```- vpn_country: us```<br />&nbsp;&nbsp;&nbsp;&nbsp;```target_country: us``` <br /> The last version is providing all desired VPN and target countries in lists. In this case, each VPN country will be paired with each target country.<br />```groups:```<br />&nbsp;&nbsp;&nbsp;&nbsp;```multi:```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```vpns: [nl, us]```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```targets: [nl, us]``` |
| `vpns` | This section defines which providers should be used, the details of technologies to use and credentials | ```vpns:```<br />```- name: nordvpn-app```<br />&nbsp;&nbsp;&nbsp;&nbsp;```credentials:```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```username: test```<br/>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```password: test```<br />&nbsp;&nbsp;&nbsp;&nbsp;```technologies:```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```- name: openvpn```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```protocols: [udp, tcp]```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```- name: nordlynx``` |
| `sinks` | Data sinks define where the test data should be stored. Note: only one sink should be marked 'as_backup: yes'. | Sqlite database sink:<br />```sinks:```<br />&nbsp;&nbsp;&nbsp;&nbsp;```- name: sqlite```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```url: /var/run/vpnspeed/vpnspeed.db```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```as_backup: yes```<br />CSV style backup, useful for easier data debugging:<br />&nbsp;&nbsp;&nbsp;&nbsp;```- name: csv```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```url: /var/run/vpnspeed/vpnspeed.csv```<br />&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;```as_backup: yes``` |
