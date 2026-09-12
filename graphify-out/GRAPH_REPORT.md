# Graph Report - .  (2026-09-12)

## Corpus Check
- 56 files · ~67,889 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 885 nodes · 1651 edges · 99 communities (83 shown, 16 thin omitted)
- Extraction: 99% EXTRACTED · 1% INFERRED · 0% AMBIGUOUS · INFERRED: 22 edges (avg confidence: 0.67)
- Token cost: 0 input · 0 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Intelligence API Routes|Intelligence API Routes]]
- [[_COMMUNITY_Core App Routes|Core App Routes]]
- [[_COMMUNITY_EV & Insurance APIs|EV & Insurance APIs]]
- [[_COMMUNITY_Alert & Notification Engine|Alert & Notification Engine]]
- [[_COMMUNITY_Ambulance Detection|Ambulance Detection]]
- [[_COMMUNITY_Vehicle Detection & OCR|Vehicle Detection & OCR]]
- [[_COMMUNITY_Vahan Database APIs|Vahan Database APIs]]
- [[_COMMUNITY_Dataset Generator & Live Feed|Dataset Generator & Live Feed]]
- [[_COMMUNITY_Blockchain Audit Trail|Blockchain Audit Trail]]
- [[_COMMUNITY_Blockchain & Citizen APIs|Blockchain & Citizen APIs]]
- [[_COMMUNITY_E-Challan System|E-Challan System]]
- [[_COMMUNITY_Intelligence Route Tests|Intelligence Route Tests]]
- [[_COMMUNITY_Camera & Live Demo|Camera & Live Demo]]
- [[_COMMUNITY_Camera & Trajectory Engine|Camera & Trajectory Engine]]
- [[_COMMUNITY_Gamification & Scoring|Gamification & Scoring]]
- [[_COMMUNITY_Report Generation|Report Generation]]
- [[_COMMUNITY_Database Migrations|Database Migrations]]
- [[_COMMUNITY_Safety Intelligence|Safety Intelligence]]
- [[_COMMUNITY_Officer Management|Officer Management]]
- [[_COMMUNITY_Vehicle AI Analysis|Vehicle AI Analysis]]
- [[_COMMUNITY_Community 20|Community 20]]
- [[_COMMUNITY_Community 21|Community 21]]
- [[_COMMUNITY_Community 22|Community 22]]
- [[_COMMUNITY_Community 23|Community 23]]
- [[_COMMUNITY_Community 24|Community 24]]
- [[_COMMUNITY_Community 25|Community 25]]
- [[_COMMUNITY_Community 26|Community 26]]
- [[_COMMUNITY_Community 27|Community 27]]
- [[_COMMUNITY_Community 28|Community 28]]
- [[_COMMUNITY_Community 29|Community 29]]
- [[_COMMUNITY_Community 30|Community 30]]
- [[_COMMUNITY_Community 31|Community 31]]
- [[_COMMUNITY_Community 32|Community 32]]
- [[_COMMUNITY_Community 33|Community 33]]
- [[_COMMUNITY_Community 34|Community 34]]
- [[_COMMUNITY_Community 35|Community 35]]
- [[_COMMUNITY_Community 36|Community 36]]
- [[_COMMUNITY_Community 37|Community 37]]
- [[_COMMUNITY_Community 38|Community 38]]
- [[_COMMUNITY_Community 39|Community 39]]
- [[_COMMUNITY_Community 40|Community 40]]
- [[_COMMUNITY_Community 41|Community 41]]
- [[_COMMUNITY_Community 42|Community 42]]
- [[_COMMUNITY_Community 43|Community 43]]
- [[_COMMUNITY_Community 44|Community 44]]
- [[_COMMUNITY_Community 45|Community 45]]
- [[_COMMUNITY_Community 46|Community 46]]
- [[_COMMUNITY_Community 47|Community 47]]
- [[_COMMUNITY_Community 48|Community 48]]
- [[_COMMUNITY_Community 49|Community 49]]
- [[_COMMUNITY_Community 50|Community 50]]
- [[_COMMUNITY_Community 51|Community 51]]
- [[_COMMUNITY_Community 52|Community 52]]
- [[_COMMUNITY_Community 53|Community 53]]
- [[_COMMUNITY_Community 54|Community 54]]
- [[_COMMUNITY_Community 55|Community 55]]
- [[_COMMUNITY_Community 56|Community 56]]
- [[_COMMUNITY_Community 57|Community 57]]
- [[_COMMUNITY_Community 58|Community 58]]
- [[_COMMUNITY_Community 59|Community 59]]
- [[_COMMUNITY_Community 60|Community 60]]
- [[_COMMUNITY_Community 61|Community 61]]
- [[_COMMUNITY_Community 62|Community 62]]
- [[_COMMUNITY_Community 63|Community 63]]
- [[_COMMUNITY_Community 64|Community 64]]
- [[_COMMUNITY_Community 65|Community 65]]
- [[_COMMUNITY_Community 66|Community 66]]
- [[_COMMUNITY_Community 67|Community 67]]
- [[_COMMUNITY_Community 68|Community 68]]
- [[_COMMUNITY_Community 69|Community 69]]
- [[_COMMUNITY_Community 70|Community 70]]
- [[_COMMUNITY_Community 71|Community 71]]
- [[_COMMUNITY_Community 72|Community 72]]
- [[_COMMUNITY_Community 73|Community 73]]
- [[_COMMUNITY_Community 74|Community 74]]
- [[_COMMUNITY_Community 75|Community 75]]
- [[_COMMUNITY_Community 76|Community 76]]
- [[_COMMUNITY_Community 77|Community 77]]
- [[_COMMUNITY_Community 78|Community 78]]
- [[_COMMUNITY_Community 79|Community 79]]
- [[_COMMUNITY_Community 80|Community 80]]
- [[_COMMUNITY_Community 81|Community 81]]
- [[_COMMUNITY_Community 82|Community 82]]
- [[_COMMUNITY_Community 83|Community 83]]
- [[_COMMUNITY_Community 84|Community 84]]
- [[_COMMUNITY_Community 85|Community 85]]
- [[_COMMUNITY_Community 86|Community 86]]
- [[_COMMUNITY_Community 87|Community 87]]
- [[_COMMUNITY_Community 88|Community 88]]
- [[_COMMUNITY_Community 89|Community 89]]
- [[_COMMUNITY_Community 90|Community 90]]
- [[_COMMUNITY_Community 92|Community 92]]
- [[_COMMUNITY_Community 93|Community 93]]
- [[_COMMUNITY_Community 94|Community 94]]
- [[_COMMUNITY_Community 95|Community 95]]
- [[_COMMUNITY_Community 96|Community 96]]
- [[_COMMUNITY_Community 98|Community 98]]

## God Nodes (most connected - your core abstractions)
1. `_get_conn()` - 51 edges
2. `_get_conn()` - 46 edges
3. `_get_conn()` - 24 edges
4. `ViolationEngine` - 24 edges
5. `lookup_owner()` - 20 edges
6. `TestIntelligenceRoutesAndRBAC` - 18 edges
7. `record_challan_on_blockchain()` - 15 edges
8. `calculate_fine()` - 15 edges
9. `init_safety_tables()` - 14 edges
10. `analyze_demo_video()` - 13 edges

## Surprising Connections (you probably didn't know these)
- `Saarthi AI Traffic Safety Assistant` --semantically_similar_to--> `TrafficGuard Copilot Operational AI Assistant`  [INFERRED] [semantically similar]
  FEATURES.md → templates/intelligence.html
- `SafeRotatingFileHandler` --uses--> `ViolationEngine`  [INFERRED]
  app.py → violation_engine.py
- `PipelineMetrics` --uses--> `ViolationEngine`  [INFERRED]
  app.py → violation_engine.py
- `TestNoHelmet` --uses--> `ViolationEngine`  [INFERRED]
  tests/test_violations.py → violation_engine.py
- `TestTripleRiding` --uses--> `ViolationEngine`  [INFERRED]
  tests/test_violations.py → violation_engine.py

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **AI Detection & Violation Processing Pipeline** — concept_yolov8_detection, concept_bytetrack, concept_anpr_ocr, concept_violation_engine, concept_helmet_detection, concept_triple_riding, concept_wrong_way [EXTRACTED 1.00]
- **Intelligence Command Operations Suite** — templates_intelligence_html, concept_vehicle_trajectory, concept_risk_intelligence, concept_signal_simulation, concept_policy_simulation, concept_enforcement_effectiveness, concept_corridor_intelligence, concept_copilot_ai [EXTRACTED 1.00]
- **Citizen-Facing Service Ecosystem** — templates_citizen_html, templates_verify_html, feature_citizen_portal, feature_suraksha_gamification, feature_qr_verification, feature_blockchain_audit, concept_privacy_masking [INFERRED 0.85]

## Communities (99 total, 16 thin omitted)

### Community 0 - "Intelligence API Routes"
Cohesion: 0.06
Nodes (42): api_intelligence_copilot(), api_intelligence_corridors(), api_intelligence_effectiveness(), api_intelligence_incidents(), api_intelligence_journeys(), api_intelligence_officers(), api_intelligence_overview(), api_intelligence_risks() (+34 more)

### Community 1 - "Core App Routes"
Cohesion: 0.05
Nodes (44): advanced_features_hub(), ai_safety_page(), analytics(), api_city_stats(), api_emission_weekly(), api_ev_chart(), api_insurance_stats(), api_pedestrian_hotspots() (+36 more)

### Community 2 - "EV & Insurance APIs"
Cohesion: 0.06
Nodes (49): api_ev_map(), api_ev_nearby(), api_ev_reserve(), api_ev_stats(), api_insurance_claim(), api_insurance_pending(), api_near_misses_new(), api_parking_tow() (+41 more)

### Community 3 - "Alert & Notification Engine"
Cohesion: 0.08
Nodes (29): check_blacklist(), check_repeat_offender(), trigger_on_violation_detection(), bot_simulator_chat(), _is_email_configured(), _is_meta_wa_configured(), _is_twilio_configured(), NotificationService (+21 more)

### Community 4 - "Ambulance Detection"
Cohesion: 0.08
Nodes (33): AmbulanceDetector, auto_dispatch_services(), clear_ambulance_route(), detect_ambulance_frame(), get_accident_history(), get_accident_stats(), get_active_ambulances(), _get_conn() (+25 more)

### Community 5 - "Vehicle Detection & OCR"
Cohesion: 0.12
Nodes (23): overlap_ratio(), VehicleTrack — Image Detection Script Runs detection on all images in the image, Fraction of boxA covered by boxB., read_plate(), _best_match(), _correct(), _find_pattern(), is_valid_indian_plate() (+15 more)

### Community 6 - "Vahan Database APIs"
Cohesion: 0.11
Nodes (18): Real Vahan lookup API: returns the live Vahan database payload or procedural fal, vahan_lookup_api(), vehicle_compare_api(), TestVahanPrivacy, TestVahanDatabase, _generate_realistic_vehicle(), get_vahan_mode(), get_vehicle_comparison() (+10 more)

### Community 7 - "Dataset Generator & Live Feed"
Cohesion: 0.11
Nodes (22): generate_single_event(), _generator_loop(), get_city_stats(), _get_conn(), get_live_feed_data(), get_realtime_kpis(), get_recent_events(), TrafficGuard Pro — AI Real-Time Dataset Generator Continuously generates realis (+14 more)

### Community 8 - "Blockchain Audit Trail"
Cohesion: 0.17
Nodes (14): compute_block_hash(), init_blockchain_table(), Tamper-Evident Cryptographic Audit Ledger for TrafficGuard Pro Ensures: 1. Eve, Mathematically verify the integrity of a recorded challan against the cryptograp, Traverse the complete cryptographic audit ledger from genesis block to the tip., Initialize the tamper-evident cryptographic ledger table with index and event su, Compute SHA-256 digest of block payload., Append an immutable block to the cryptographic chain. (+6 more)

### Community 9 - "Blockchain & Citizen APIs"
Cohesion: 0.11
Nodes (20): blockchain_ledger_api(), blockchain_verify_api(), blockchain_verify_ledger_api(), citizen_violations(), download_challan(), export_csv(), _get_conn(), get_heatmap() (+12 more)

### Community 10 - "E-Challan System"
Cohesion: 0.15
Nodes (17): _load_ocr_in_background(), generate_challan(), generate_qr(), get_offence_count(), TrafficGuard Pro E-Challan & Payment Receipt PDF Generator Generates: 1. High-, Count previous violations recorded for this plate., Generate high-contrast QR code for digital verification and payment., Generate Official High-Resolution Traffic Enforcement E-Challan PDF. (+9 more)

### Community 12 - "Camera & Live Demo"
Cohesion: 0.12
Nodes (17): detect_seatbelt_frame(), Conservative seatbelt line detector for a front-facing car crop., broadcast_sse(), citizen_file_dispute(), correct_plate(), _draw_annotations(), ensure_live_models(), _live_demo_report() (+9 more)

### Community 13 - "Camera & Trajectory Engine"
Cohesion: 0.20
Nodes (13): add_camera(), list_cameras(), search_plate(), compute_heatmap(), _connect(), _ensure_schema(), match_plates_across_cameras(), _parse_timestamp() (+5 more)

### Community 14 - "Gamification & Scoring"
Cohesion: 0.16
Nodes (11): suraksha_leaderboard_api(), suraksha_score_api(), calculate_suraksha_score(), generate_certificate_data(), get_safest_zones_leaderboard(), get_suraksha_tier(), Traffic Safety Gamification Engine & "Suraksha" Safe Driving Scoring Provides:, Returns community safety compliance rankings by city sector. (+3 more)

### Community 15 - "Report Generation"
Cohesion: 0.15
Nodes (14): blackspots_api(), evidence_verify_api(), Compute and verify SHA-256 cryptographic digest of violation frame screenshot., vehicle_risk_api(), blackspots(), level(), near_miss(), Data-first AI Safety & Road Risk Intelligence Engine for TrafficGuard Pro Featu (+6 more)

### Community 16 - "Database Migrations"
Cohesion: 0.17
Nodes (12): demo_analyze_api(), demo_report_api(), Store an uploaded video in the local video catalog without running inference in, Trigger deep frame-by-frame AI analysis of demo traffic video with real-time SSE, Retrieve full execution and audit report for a demo video., start_video(), upload_video(), get_video_metadata() (+4 more)

### Community 17 - "Safety Intelligence"
Cohesion: 0.14
Nodes (14): admin_blacklist_add(), admin_blacklist_list(), _auto_seed(), emergency_events_api(), init_db(), Retrieve green-corridor ambulance/emergency priority vehicle events., Seed 25 realistic Indian violation records., add_blacklist_entry() (+6 more)

### Community 18 - "Officer Management"
Cohesion: 0.10
Nodes (14): api_drunk_heatmap(), api_emission_heatmap(), api_ev_range(), api_predict_accident(), alert_police_for_impaired_driver(), calculate_ev_range(), create_pollution_heatmap_data(), get_drunk_driving_heatmap() (+6 more)

### Community 19 - "Vehicle AI Analysis"
Cohesion: 0.18
Nodes (9): admin_disputes_list(), admin_resolve_dispute(), get_disputes(), File a formal citizen dispute against an issued challan within the statutory 15-, List citizen disputes for administrative review., Officer adjudication on a citizen dispute ('ACCEPTED' or 'REJECTED').     If AC, resolve_dispute(), submit_dispute() (+1 more)

### Community 20 - "Community 20"
Cohesion: 0.22
Nodes (5): Dashcam: wrong-way rider moves toward camera (cy decreasing fast)., Static camera: wrong-way rider moves toward camera (cy increasing fast)., Slow movement (normal traffic) should not trigger wrong-way., Bikes near frame edges are excluded to avoid entry/exit false positives., TestWrongWay

### Community 21 - "Community 21"
Cohesion: 0.23
Nodes (7): chatbot_ask(), answer_traffic_query(), _is_hindi(), Saarthi AI — Bilingual Traffic Safety & RTO Knowledge Assistant Pre-loaded with, Detect if string contains Devanagari script., Process traffic rule queries using semantic keyword matching with automatic Hind, TestSaarthiChatbot

### Community 22 - "Community 22"
Cohesion: 0.27
Nodes (7): officers_leaderboard_api(), get_officer_leaderboard(), init_officers_table(), Officer Management, RBAC & Enforcement Gamification for TrafficGuard Pro Handle, Return live sorted performance ranking of enforcement officers., Unit Tests for TrafficGuard Pro Hackathon Upgrades Tests: 1. Vahan National Da, TestOfficerManagement

### Community 23 - "Community 23"
Cohesion: 0.29
Nodes (4): calculate_fine(), Calculate total fine with habitual offender severity multiplier., VehicleTrack — Unit Tests Run with: python -m pytest tests/ -v, TestFineCalculation

### Community 24 - "Community 24"
Cohesion: 0.20
Nodes (10): detect_school_zone_violation(), _get_conn(), get_vehicle_health_stats(), Get fleet-wide vehicle health statistics., Seed school data and bus tracking., Detect speeding or parking violations in school zones., Seed toll plazas and generate transaction history., seed_schools_and_buses() (+2 more)

### Community 25 - "Community 25"
Cohesion: 0.20
Nodes (10): api_driver_risk(), api_insurance_premium(), api_sync_scores(), calculate_insurance_premium(), calculate_risk_score(), get_risk_category(), Compute weighted driver risk score 0-100., Bulk recalculate all risk profiles. (+2 more)

### Community 26 - "Community 26"
Cohesion: 0.20
Nodes (10): Indian ANPR / EasyOCR Plate Parser, ByteTrack Multi-Object Tracking, YOLOv8 Object Detection Pipeline, Docker Compose Configuration, TrafficGuard Pro Feature Specification, TrafficGuard Pro, Render Deployment Configuration, EasyOCR (+2 more)

### Community 27 - "Community 27"
Cohesion: 0.20
Nodes (10): Blackspot Risk Score Heatmap, Habitual Offender Penalty Scaling, Cross-Camera Vehicle Journey Tracking, Advanced Analytics & Trend Intelligence, Vehicle Fleet Comparison & Repeat Offender Profiling, Real-Time Geolocation Hotspot Heat Map, Predictive Analytics & Peak Violation Hours, National Vahan Database Integration (+2 more)

### Community 28 - "Community 28"
Cohesion: 0.29
Nodes (10): i18n Translation Dictionary (EN/HI/PB), SSE Push Event Broadcasting, Multi-Language Support (i18n), Server-Sent Events Real-Time Notification Stream, kafka-python, System Analytics Dashboard, Citizen Public Portal, Command Centre Dashboard (+2 more)

### Community 30 - "Community 30"
Cohesion: 0.22
Nodes (8): get_vehicle_category_breakdown(), TrafficGuard Pro — Hazard Reporting, Vehicle Health, School Safety & Toll Module, Simulate SMS maintenance alert to vehicle owner., Seed initial hazard data for demo., Get vehicle type breakdown for charts., seed_hazard_data(), send_maintenance_alert(), api_toll_breakdown()

### Community 31 - "Community 31"
Cohesion: 0.22
Nodes (9): SHA-256 Cryptographic Block Hash Chain, Role-Based Access Control (RBAC), Cryptographic Blockchain Audit Ledger, Mobile-Responsive Citizen Public Portal, Automated Monthly PDF Reports, QR-Based Tamper-Proof Challan Verification, Suraksha Safe Driving Gamification, QR Code Library (+1 more)

### Community 32 - "Community 32"
Cohesion: 0.28
Nodes (9): TrafficGuard Copilot Operational AI Assistant, Helmet Detection Violation, Motor Vehicles Act 1988 & 2019 Amendments, Near-Miss Event Detection, Triple Riding Detection, ViolationEngine Processing Pipeline, Wrong-Way Detection, Saarthi AI Traffic Safety Assistant (+1 more)

### Community 33 - "Community 33"
Cohesion: 0.25
Nodes (8): peak_hours_api(), predictive_recommendations_api(), Actionable AI directives for interceptor patrols and safety checkpoints., recommendations_api(), get_peak_violation_hours(), get_predictive_recommendations(), Generates actionable AI directives for Traffic Police interceptor deployment., Returns hour-by-hour violation counts (00 to 23) for predictive charts.

### Community 34 - "Community 34"
Cohesion: 0.29
Nodes (7): _correct_plate(), get_overlap(), get_writer(), VehicleTrack — Batch Video Processor Processes all videos in /videos folder and, Try codecs in order until one works on this machine.     Mac: avc1 works best., Fraction of boxA covered by boxB., read_plate()

### Community 38 - "Community 38"
Cohesion: 0.38
Nodes (4): Any, publish_event(), Kafka event bus for TrafficGuard Pro.  The project keeps all legacy features a, TrafficGuardEventBus

### Community 40 - "Community 40"
Cohesion: 0.33
Nodes (5): citizen_pay(), download_receipt(), generate_receipt(), Generate Official Payment Settlement Receipt PDF for paid challans., TestPdfGeneration

### Community 41 - "Community 41"
Cohesion: 0.40
Nodes (5): index(), build_demo_catalog(), _is_file_present(), Metadata and status helpers for the seven-file hackathon demo library., Return only files present on disk, with observed rather than fabricated status.

### Community 42 - "Community 42"
Cohesion: 0.33
Nodes (3): make_camera_state(), metrics_api(), PipelineMetrics

### Community 43 - "Community 43"
Cohesion: 0.47
Nodes (6): Arterial Corridor Delay Analytics, Enforcement Intervention Effectiveness Tracking, Policy & Deployment What-If Simulator, Webster Formula Signal Timing Simulator, Intelligence Command Grid, Intelligence Operations Login

### Community 44 - "Community 44"
Cohesion: 0.33
Nodes (6): Emergency Vehicle Detection Alerts, Multi-Dimensional Risk Intelligence, High-Risk Vehicle Scoring, Weather-Aware Risk Adjustment, WhatsApp + SMS Multi-Channel Notifications, AI Safety Intelligence Page

### Community 45 - "Community 45"
Cohesion: 0.40
Nodes (4): download_monthly_report(), generate_monthly_report(), Automated Report Generator for TrafficGuard Pro Generates comprehensive PDF rep, Generate official multi-section Monthly Traffic Enforcement Report PDF.

### Community 46 - "Community 46"
Cohesion: 0.50
Nodes (4): near_misses_api(), Retrieve recorded near-miss proximity incidents., get_near_misses(), Retrieve recorded near-miss proximity incidents.

### Community 47 - "Community 47"
Cohesion: 0.50
Nodes (4): Pending items in the human-in-the-loop evidence review queue., reviews_api(), Returns pending items in the human-in-the-loop review queue., reviews()

### Community 48 - "Community 48"
Cohesion: 0.50
Nodes (4): Approve, Reject, or Issue challan from review queue., review_action_api(), Approve, Reject, or Issue a challan from the Human-in-the-Loop review queue., update_review_action()

### Community 49 - "Community 49"
Cohesion: 0.50
Nodes (3): fix_yaml(), VehicleTrack — Complete Model Evaluation Evaluates:   1. best.pt  — custom hel, Roboflow yamls use paths like ../train/images (relative, going UP).     This is

### Community 50 - "Community 50"
Cohesion: 0.67
Nodes (3): make_violations(), VehicleTrack — Database Seed Script Populates violations.db with realistic samp, seed()

### Community 51 - "Community 51"
Cohesion: 0.50
Nodes (3): builds, routes, version

### Community 52 - "Community 52"
Cohesion: 0.67
Nodes (3): generate_roadworthiness_certificate(), Generate blockchain-backed roadworthiness certificate., api_roadworthiness_cert()

### Community 53 - "Community 53"
Cohesion: 0.67
Nodes (3): get_active_hazards(), Get all unresolved hazard reports for map display., api_hazard_active()

### Community 54 - "Community 54"
Cohesion: 0.67
Nodes (3): get_bus_locations(), Get real-time bus locations for all school buses., api_bus_tracking()

### Community 55 - "Community 55"
Cohesion: 0.67
Nodes (3): get_citizen_leaderboard(), Get top citizen reporters., api_hazard_leaderboard()

### Community 56 - "Community 56"
Cohesion: 0.67
Nodes (3): get_faulty_vehicles(), Get list of vehicles with detected faults., api_faulty_vehicles()

### Community 57 - "Community 57"
Cohesion: 0.67
Nodes (3): get_hazard_stats(), Get hazard reporting statistics., api_hazard_stats()

### Community 58 - "Community 58"
Cohesion: 0.67
Nodes (3): get_recent_transactions(), Get recent toll transactions., api_toll_transactions()

### Community 59 - "Community 59"
Cohesion: 0.67
Nodes (3): get_school_zone_stats(), Get school zone safety statistics., api_school_stats()

### Community 60 - "Community 60"
Cohesion: 0.67
Nodes (3): get_schools_list(), Get all schools with zone info for map display., api_school_zones()

### Community 61 - "Community 61"
Cohesion: 0.67
Nodes (3): get_toll_plazas(), Get all toll plaza info., api_toll_plazas()

### Community 62 - "Community 62"
Cohesion: 0.67
Nodes (3): get_toll_revenue(), Get revenue statistics for toll plaza(s)., api_toll_revenue()

### Community 63 - "Community 63"
Cohesion: 0.67
Nodes (3): get_toll_stats(), Get overall toll system statistics., api_toll_stats()

### Community 64 - "Community 64"
Cohesion: 0.67
Nodes (3): get_work_order_tracker(), Get government work order status for accountability dashboard., api_work_orders()

### Community 65 - "Community 65"
Cohesion: 0.67
Nodes (3): inspect_vehicle_health(), AI-simulated vehicle health inspection from camera feed., api_vehicle_inspect()

### Community 66 - "Community 66"
Cohesion: 0.67
Nodes (3): process_toll(), Process automatic toll deduction for a vehicle., api_toll_collect()

### Community 67 - "Community 67"
Cohesion: 0.67
Nodes (3): Send parent alerts about bus departure/arrival., send_parent_alert(), api_parent_alert()

### Community 68 - "Community 68"
Cohesion: 0.67
Nodes (3): Accept a citizen hazard report and run AI verification., submit_hazard_report(), api_hazard_report()

### Community 69 - "Community 69"
Cohesion: 0.67
Nodes (3): api_driver_profiles(), get_all_risk_profiles(), Get all driver risk profiles.

### Community 70 - "Community 70"
Cohesion: 0.67
Nodes (3): api_drunk_detect(), analyze_vehicle_for_impairment(), Multi-modal drunk driving detection simulation.

### Community 71 - "Community 71"
Cohesion: 0.67
Nodes (3): api_drunk_offenders(), get_offender_list(), Get drunk driving offender list.

### Community 72 - "Community 72"
Cohesion: 0.67
Nodes (3): api_drunk_stats(), get_drunk_driving_stats(), Return drunk driving detection statistics.

### Community 73 - "Community 73"
Cohesion: 0.67
Nodes (3): api_emission_analyze(), analyze_vehicle_emission(), Simulate AI smoke color detection and emission analysis.

### Community 74 - "Community 74"
Cohesion: 0.67
Nodes (3): api_emission_hotspots(), get_pollution_hotspots(), Return top pollution hotspot data.

### Community 75 - "Community 75"
Cohesion: 0.67
Nodes (3): api_emission_stats(), get_emission_stats(), Return emission monitoring statistics.

### Community 76 - "Community 76"
Cohesion: 0.67
Nodes (3): api_ev_reward(), Award green points and cashback to EV owners., reward_ev_vehicle()

### Community 77 - "Community 77"
Cohesion: 0.67
Nodes (3): api_insurance_approve(), approve_claim(), Approve an insurance claim and calculate payout.

### Community 78 - "Community 78"
Cohesion: 0.67
Nodes (3): api_live_feed(), get_live_feed_data(), Get latest AI-generated real-time traffic events.

### Community 79 - "Community 79"
Cohesion: 0.67
Nodes (3): api_parking_detect(), detect_parking_violation(), Simulate parking violation detection.

### Community 80 - "Community 80"
Cohesion: 0.67
Nodes (3): api_parking_stats(), get_parking_stats(), Get parking enforcement statistics.

### Community 81 - "Community 81"
Cohesion: 0.67
Nodes (3): api_parking_violations(), get_active_parking_violations(), Get unpaid parking violations.

### Community 82 - "Community 82"
Cohesion: 0.67
Nodes (3): api_parking_zones(), get_parking_zones(), Return all parking zones for map.

### Community 83 - "Community 83"
Cohesion: 0.67
Nodes (3): api_pedestrian_detect(), Simulate pedestrian detection from camera feed., simulate_pedestrian_detection()

### Community 84 - "Community 84"
Cohesion: 0.67
Nodes (3): api_realtime_kpis(), get_realtime_kpis(), Get live KPI metrics for dashboard.

### Community 85 - "Community 85"
Cohesion: 0.67
Nodes (3): api_risk_distribution(), get_risk_distribution(), Get risk category distribution for pie chart.

### Community 86 - "Community 86"
Cohesion: 0.67
Nodes (3): api_risk_stats(), get_risk_stats(), Get risk scoring statistics.

## Knowledge Gaps
- **24 isolated node(s):** `version`, `builds`, `routes`, `TrafficGuard Pro Feature Specification`, `EasyOCR` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **16 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `ViolationEngine` connect `Community 29` to `Core App Routes`, `Community 36`, `Community 37`, `Community 39`, `Community 42`, `E-Challan System`, `Camera & Trajectory Engine`, `Community 20`, `Community 87`, `Community 23`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Why does `TestIntelligenceRoutesAndRBAC` connect `Intelligence Route Tests` to `Intelligence API Routes`?**
  _High betweenness centrality (0.034) - this node is a cross-community bridge._
- **Why does `TestWrongWay` connect `Community 20` to `Community 29`, `Community 23`?**
  _High betweenness centrality (0.022) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `ViolationEngine` (e.g. with `PipelineMetrics` and `SafeRotatingFileHandler`) actually correct?**
  _`ViolationEngine` has 7 INFERRED edges - model-reasoned connections that need verification._
- **What connects `TrafficGuard Pro — Hazard Reporting, Vehicle Health, School Safety & Toll Module`, `Seed initial hazard data for demo.`, `Accept a citizen hazard report and run AI verification.` to the rest of the system?**
  _254 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Intelligence API Routes` be split into smaller, more focused modules?**
  _Cohesion score 0.06127946127946128 - nodes in this community are weakly interconnected._
- **Should `Core App Routes` be split into smaller, more focused modules?**
  _Cohesion score 0.050314465408805034 - nodes in this community are weakly interconnected._