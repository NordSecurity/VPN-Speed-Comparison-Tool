#!/usr/bin/expect -f
set username [lindex $argv 0];
set password [lindex $argv 1];
spawn purevpn-cli -li
expect "*name: "
send "${username}\r"
expect "*ssword: "
send "${password}\r"
expect #