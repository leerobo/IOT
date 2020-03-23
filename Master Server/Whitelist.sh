#!/bin/sh

# ipset-country 
# =============
# Block countries using iptables + ipset + ipdeny.com
# - run this script from cron, e.g. /etc/cron.daily
# - to run on boot you can also add it to e.g. /etc/rc.local

# NOTE: this script will insert an iptables REJECT rule for ipset

# also available and more extensive:
# https://github.com/tokiclover/dotfiles/blob/master/bin/ips.bash

# CONFIGURATION:
# ==============

# OS: "auto", "manual", "debian" or "redhat" (default is auto)
# manual example: confdir="/etc/iptables", rulefile="${confdir}/myrules"
distro="auto"

# specify countries to block as ISOCODE,Name
# multiple entries should be seperated by semicolon
# example: "CN,China; United States,US Russia,RU"
country="CN,China"

# create logips chain and log rejects [0/1]
logips=1

# using aggregated block zone files, which are smaller
# or for full zone files change to: "/data/countries/<ctyiso>.zone"
ipdeny_url="http://www.ipdeny.com/ipblocks/data/aggregated"

# log to file, or to disable: "/dev/null 2>&1"
log="/var/log/ipset-country.log"

# END OF CONFIG
# ==============

# ipset cmds  : ipset list | test setname <ip> | flush | destroy
# rc ipset    : ips_a = ipset add, ips_c = create
# rc iptables : ipt_i = insert rule,  ipt_j = reject rule, ipt_n = new chain
#               ipt_l = log rule, ipt_r = restore

func_msg() { echo "$( date +%F\ %T ) $*"; }

# set confdir/rulefile according to distro
func_dist_auto() {
  if [ -s /etc/os-release ]; then
    if grep -iq "debian\|ubuntu" /etc/os-release; then distro="debian"
    elif grep -iq "centos\|fedora\|rhel" /etc/os-release; then distro="redhat"; fi
  else
    if [ -s /etc/debian_version ]; then distro="debian"
    elif [ -s /etc/redhat-release ]; then distro="redhat"; fi
  fi
}
func_dist_vars() {
  if [ "$distro" = "debian" ]; then confdir="/etc/iptables";  rulefile="${confdir}/rules.v4"
  elif [ "$distro" = "redhat" ]; then confdir="/etc/sysconfig"; rulefile="${confdir}/iptables"
  fi
}
if [ "$distro" = "auto" ]; then func_dist_auto; fi
func_dist_vars
if [ -z "$confdir" ] || [ -z "$rulefile" ]; then
  if [ "$distro" = "manual" ]; then
    echo "warning: distro set to manual but confdir/rulefile not set, trying autodetect..."
    func_dist_auto; func_dist_vars
  else
    echo "error: could not set confdir or rulefile, exiting..."; exit 1
  fi
fi

IFS=";"
for c in $country; do
  ctyiso="$( echo "$c" | tr '[:upper:]' '[:lower:]' | cut -d"," -f 1 | sed -e 's/\(^ \+\| \+$\)//g' )"
  ctyname="$( echo "$c" | tr '[:upper:]' '[:lower:]' | cut -d"," -f 2 | sed -e 's/\(^ \+\| \+$\)//g' -e 's/ /_/g' )"
  zonefile="${ctyiso}-aggregated.zone"
  if [ "$ctyname" != "" ]; then
    # create a new set using type hash
    { ipset list -terse "$ctyname" >/dev/null 2>&1 || ipset create "$ctyname" hash:net; } && ips_c="OK" || ips_c="NOK"
    func_msg "ipset: create set \"$ctyname\" - $ips_c"

    # download zone file and verify using md5sum
    wget -q -O "/tmp/$zonefile.$$" "$ipdeny_url/$zonefile"
    md5src="$( wget -q -O - "$ipdeny_url/MD5SUM" | grep "$zonefile" | cut -d" " -f 1 )"
    md5chk="$( md5sum "/tmp/$zonefile.$$" | cut -d" " -f 1 )"

    if [ "$md5src" = "$md5chk" ]; then
      mv "/tmp/$zonefile.$$" "${confdir}/$zonefile" && zf="OK" || zf="NOK"
      func_msg "zonefile: get \"$zonefile\" - $zf"

      # add blocks to ipset
      c=0; while read -r l; do
          ipset -A -exist -quiet "$ctyname" "$l" && c=$((c+1))
      done < "${confdir}/$zonefile" >/dev/null 2>&1 && ips_a="OK" || ips_a="NOK"
      func_msg "ipset: add \"$zonefile\" to \"$ctyname\" - $ips_a - $c entries"

      # restore iptables and insert rules for ipset
      /sbin/iptables-restore < "$rulefile" && ipt_r="OK" || ipt_r="NOK"
      func_msg "iptables: restore - $ipt_r"
        # insert at line number 1 or last line in input chain
        rulenum=1; rulenum=$(( $(iptables -S INPUT|wc -l) - 1 ))
        if [ "$logips" -eq 1 ]; then
          # check if logips chain already exists, if not create it
          if /sbin/iptables-save | grep -q "LOGIPS"; then
            ipt_n="already exists"
          else
            { /sbin/iptables -N LOGIPS && ipt_n="OK" || ipt_n="NOK"; }
          fi

          # check if logips chain and ipset rules exist, if not insert them
          if /sbin/iptables-save | grep -q "LOGIPS.*log"; then
            ipt_l="already exists"
          else
            /sbin/iptables -A LOGIPS -m limit --limit 10/min -j LOG --log-prefix "IPS REJECT: " --log-level 6 && \
            ipt_l="OK" || ipt_l="NOK"
          fi
          if /sbin/iptables-save | grep -q "LOGIPS.*reject"; then
            ipt_j="already exists"
          else
            /sbin/iptables -A LOGIPS -j REJECT --reject-with icmp-port-unreachable && ipt_j="OK" || ipt_j="NOK"
          fi
          if /sbin/iptables-save | grep -q "match-set.*$ctyname.*LOGIPS"; then
            ipt_i="already exists"
          else
            /sbin/iptables -I INPUT "$rulenum" -p tcp -m set --match-set "$ctyname" src -j LOGIPS && \
            ipt_i="OK" || ipt_i="NOK"
          fi
        fi

        # check if logsips rules do not exist and if so it's because:
        #   a) logips=0   b) previous cmds failed -> for both cases insert ipset reject rule
        if ! /sbin/iptables-save | grep -q "\-A LOGIPS"; then
          # also check if ipset rule doesnt exist
          if /sbin/iptables-save | grep -q "match-set.*$ctyname.*REJECT"; then
            ipt_i="already exists"
          else
            /sbin/iptables -I INPUT "$rulenum" -p tcp -m set --match-set "$ctyname" src -j REJECT --reject-with icmp-port-unreachable && \
            ipt_i="OK" || ipt_i="NOK"; ipt_n="disabled"; ipt_l="disabled"; ipt_j="disabled"
          fi
        fi
        func_msg "iptables: create log chain - $ipt_n"
        func_msg "iptables: append log rule - $ipt_l, append reject rule - $ipt_j"
        func_msg "iptables: insert ipset rule - $ipt_i"
      fi
    fi
  [ -f "/tmp/$zonefile.$$" ] && rm "/tmp/$zonefile.$$"
done >>"$log"
