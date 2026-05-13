; Managed by pyinfra. Source: dns/files/zones/_common.inc
; Shared apex records for every zone served from egnor-2020. Included by
; each per-zone .zone file *after* its $ORIGIN and SOA. Edit here to update
; every zone in lockstep.
;
; ns1.eacs.io is this host as primary; ns1..5.he.net is the Hurricane
; Electric free-secondary set (registered per-zone at dns.he.net, which
; pulls via AXFR — see the he_xfr ACL in knot.conf).

@   1h NS   ns1.eacs.io.
@   1h NS   ns1.he.net.
@   1h NS   ns2.he.net.
@   1h NS   ns3.he.net.
@   1h NS   ns4.he.net.
@   1h NS   ns5.he.net.

@   1h A    104.200.25.248
@   1h AAAA 2600:3c01::f03c:92ff:feeb:cac3
@   1h AAAA 2600:3c01:e000:3d3::1

; Wildcard so unrecognized subdomains (and the unprobed ones) resolve to
; the apex. Matches single-label names only; multi-label names that need
; to resolve here (e.g. egnor.approximately.competent.services) must have
; explicit records in their per-zone file.
*   1h CNAME @
