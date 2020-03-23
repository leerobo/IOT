#!/bin/bash

iptables="/sbin/iptables"
tempdir="/tmp"
sourceURL="http://www.ipdeny.com/ipblocks/data/countries/"
#
[ -e /sbin/ipset ] && ipset="/sbin/ipset" || ipset="/usr/sbin/ipset"
#
# Verifying the number of arguments
$ipset flush whitelist &>/dev/null
$ipset create whitelist hash:net &>/dev/null

(
for ip in $(curl -1ks http://www.ipdeny.com/ipblocks/data/countries/gb.zone); 
do ipset -q add whitelist $ip; 
done
)&
echo "GB Added to Whitelist"

(
for ip in $(curl -1ks http://www.ipdeny.com/ipblocks/data/countries/se.zone); 
do ipset -q add whitelist $ip; 
done
)&
echo "SE Added to Whitelist"

$iptables-restore < /home/leerobo/boot/iptables-whitelist

echo "Whitelist Applied to IPTABLES"
