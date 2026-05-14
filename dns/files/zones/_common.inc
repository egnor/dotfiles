; Managed by pyinfra. Source: dns/files/zones/_common.inc
; Shared apex records for every zone served from egnor-2020.
; Included by each per-zone .zone file *after* its $ORIGIN and SOA.

; this host is the primary nameserver
@   1h NS   ns1.eacs.io.

; Hurricane Electric free secondaries, registered per-zone at dns.he.net.
@   1h NS   ns1.he.net.
@   1h NS   ns2.he.net.
@   1h NS   ns3.he.net.
@   1h NS   ns4.he.net.
@   1h NS   ns5.he.net.

@   1h A    104.200.25.248
@   1h AAAA 2600:3c01::f03c:92ff:feeb:cac3
@   1h AAAA 2600:3c01:e000:3d3::1

; Single-label-deep wildcard for extra subdomains (www., etc).
; Uses A/AAAA rather than CNAME to avoid replicating apex MX, TXT, etc.
*   1h A    104.200.25.248
*   1h AAAA 2600:3c01::f03c:92ff:feeb:cac3
*   1h AAAA 2600:3c01:e000:3d3::1
