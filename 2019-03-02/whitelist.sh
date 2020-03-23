for IP in $(wget -O – http://www.ipdeny.com/ipblocks/data/countries/{cn,ru,kr,pk,tw,sg,hk}.zone)
do
# ban everything - block countryX
sudo ipset add whitelist $IP
done

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

$iptables -L INPUT -n -v | grep 'match-set'




# >>>>>>>>>>>>>> Allow selected IPs
-A INPUT -s 188.122.149.74 -j ACCEPT
-A INPUT -s 83.253.193.122 -j ACCEPT
# >>>>>>>>>>>>>> Apply IPSET BlockCNTY set by /etc/blocklist.sh
-A INPUT -m set --match-set BlockCNTY src -j REJECT --reject-with icmp-port-unreachable
#
-A INPUT -i virbr0 -p udp -m udp --dport 53 -j ACCEPT
-A INPUT -i virbr0 -p tcp -m tcp --dport 53 -j ACCEPT
-A INPUT -i virbr0 -p udp -m udp --dport 67 -j ACCEPT
-A INPUT -i virbr0 -p tcp -m tcp --dport 67 -j ACCEPT
-A INPUT -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
-A INPUT -i lo -j ACCEPT
-A INPUT -j INPUT_direct
-A INPUT -j INPUT_ZONES_SOURCE
-A INPUT -j INPUT_ZONES
-A INPUT -p icmp -j ACCEPT
-A INPUT -m conntrack --ctstate INVALID -j DROP
-A INPUT -j REJECT --reject-with icmp-host-prohibited
