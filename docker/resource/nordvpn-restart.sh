#!/bin/bash

# set -x

nordvpn_is_started() {
	until nordvpn status
		do
		echo 'nordvpn not ready'
		sleep 1
	done
}

service nordvpn restart && nordvpn_is_started
