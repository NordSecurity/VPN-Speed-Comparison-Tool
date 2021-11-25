#!/bin/bash

# set -x

express_is_started() {
	until expressvpn status
		do
		echo 'expressvpn not ready'
		sleep 1
	done
}

sudo service expressvpn restart && express_is_started
