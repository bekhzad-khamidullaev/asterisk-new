CREATE TABLE IF NOT EXISTS ps_aors (
  id varchar(80) NOT NULL,
  contact varchar(255) DEFAULT NULL,
  default_expiration int DEFAULT NULL,
  mailboxes varchar(255) DEFAULT NULL,
  max_contacts int DEFAULT NULL,
  minimum_expiration int DEFAULT NULL,
  remove_existing varchar(3) DEFAULT NULL,
  qualify_frequency int DEFAULT NULL,
  authenticate_qualify varchar(3) DEFAULT NULL,
  maximum_expiration int DEFAULT NULL,
  outbound_proxy varchar(255) DEFAULT NULL,
  support_path varchar(3) DEFAULT NULL,
  qualify_timeout float DEFAULT NULL,
  voicemail_extension varchar(40) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS ps_auths (
  id varchar(80) NOT NULL,
  auth_type varchar(40) DEFAULT NULL,
  nonce_lifetime int DEFAULT NULL,
  md5_cred varchar(40) DEFAULT NULL,
  password varchar(80) DEFAULT NULL,
  realm varchar(40) DEFAULT NULL,
  username varchar(80) DEFAULT NULL,
  refresh_token varchar(255) DEFAULT NULL,
  oauth_clientid varchar(255) DEFAULT NULL,
  oauth_secret varchar(255) DEFAULT NULL,
  PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS ps_endpoints (
  id varchar(80) NOT NULL,
  transport varchar(80) DEFAULT NULL,
  aors varchar(255) DEFAULT NULL,
  auth varchar(80) DEFAULT NULL,
  context varchar(80) DEFAULT NULL,
  disallow varchar(255) DEFAULT NULL,
  allow varchar(255) DEFAULT NULL,
  direct_media varchar(3) DEFAULT NULL,
  connected_line_method varchar(80) DEFAULT NULL,
  direct_media_method varchar(80) DEFAULT NULL,
  direct_media_glare_mitigation varchar(80) DEFAULT NULL,
  disable_direct_media_on_nat varchar(3) DEFAULT NULL,
  dtmf_mode varchar(80) DEFAULT NULL,
  external_media_address varchar(80) DEFAULT NULL,
  force_rport varchar(3) DEFAULT NULL,
  from_domain varchar(255) DEFAULT NULL,
  from_user varchar(80) DEFAULT NULL,
  ice_support varchar(3) DEFAULT NULL,
  identify_by varchar(80) DEFAULT NULL,
  language varchar(20) DEFAULT NULL,
  mailboxes varchar(255) DEFAULT NULL,
  moh_suggest varchar(255) DEFAULT NULL,
  outbound_auth varchar(80) DEFAULT NULL,
  outbound_proxy varchar(255) DEFAULT NULL,
  rewrite_contact varchar(3) DEFAULT NULL,
  rtp_ipv6 varchar(3) DEFAULT NULL,
  rtp_symmetric varchar(3) DEFAULT NULL,
  send_diversion varchar(3) DEFAULT NULL,
  send_pai varchar(3) DEFAULT NULL,
  send_rpid varchar(3) DEFAULT NULL,
  timers_min_se int DEFAULT NULL,
  timers varchar(80) DEFAULT NULL,
  trust_id_inbound varchar(3) DEFAULT NULL,
  trust_id_outbound varchar(3) DEFAULT NULL,
  use_avpf varchar(3) DEFAULT NULL,
  media_encryption varchar(80) DEFAULT NULL,
  media_use_received_transport varchar(3) DEFAULT NULL,
  set_var text DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_ps_endpoints_aors (aors),
  KEY idx_ps_endpoints_transport (transport),
  KEY idx_ps_endpoints_context (context)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS ps_endpoint_id_ips (
  id varchar(80) NOT NULL,
  endpoint varchar(80) DEFAULT NULL,
  `match` varchar(255) DEFAULT NULL,
  srv_lookups varchar(3) DEFAULT NULL,
  match_header varchar(255) DEFAULT NULL,
  PRIMARY KEY (id),
  KEY idx_ps_endpoint (endpoint)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE TABLE IF NOT EXISTS ps_domain_aliases (
  id varchar(80) NOT NULL,
  domain varchar(255) DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_ps_domain_aliases_domain (domain)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

CREATE OR REPLACE VIEW vw_queue_members_asterisk AS
SELECT
  id,
  queue_name,
  interface,
  penalty,
  paused,
  member_name
FROM queue_members;

-- Example records for this environment.
-- Keep transports in pjsip.conf; use realtime only for endpoints/aors/identify/auth.
--
-- INSERT INTO ps_aors (id, contact, qualify_frequency, authenticate_qualify, qualify_timeout)
-- VALUES ('712031220', 'sip:172.27.61.5', 60, 'no', 5.0);
--
-- INSERT INTO ps_endpoints (
--   id, transport, aors, context, disallow, allow, from_domain, from_user,
--   direct_media, identify_by, force_rport, rtp_symmetric, set_var
-- ) VALUES (
--   '712031220', 'udp-ut', '712031220', 'tash-in', 'all', 'alaw,ulaw',
--   '172.27.61.5', '712031220', 'no', 'header', 'yes', 'yes',
--   'CITY=TOSHKENT;PRIO=1;WORK=09:00-04:30'
-- );
--
-- INSERT INTO ps_endpoint_id_ips (id, endpoint, match_header)
-- VALUES ('712031220', '712031220', 'To: /712031220@*/');
