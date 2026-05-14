; Managed by pyinfra. Source: dns/files/zones/_no-email.inc
; "This domain does not send or receive mail" trifecta. Include alongside
; _common.inc on zones that have no MX/SPF/DKIM of their own. MUST NOT
; be included on a mail-serving zone — two v=spf1 TXTs at the same name
; is a permerror per RFC 7208, and a null MX next to a real MX is
; nonsense.

; Null MX (RFC 7505): well-behaved senders abort at MX lookup instead
; of after a TCP refusal. Cheap kindness to receivers.
@      1h MX  0 .

; SPF hard-fail: no IP is authorized to send for this domain.
@      1h TXT "v=spf1 -all"

; DMARC reject: receivers quarantine/reject forged mail. No rua= — we
; don't care to collect forgery reports for these.
_dmarc 1h TXT "v=DMARC1; p=reject;"
