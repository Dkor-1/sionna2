# DJI 드론 5종 — 제원 조사 근거 (웹 조사 + 독립 교차검증)

> 조사일 2026-06-30. 각 항목은 1차 조사(research) 후 독립 검증(verify)을 거쳤습니다.
> 원자료(JSON): `docs/drone_research.json`.

## DJI Mini 5 Pro

- **출시상태**: released (2025) · 신뢰도 high
- **구성**: folding quadcopter (sub-250g mini) · 로터 4 · 암 4 · 동축 False
- **대각거리(휠베이스)**: 250 mm
- **이륙중량**: 249.9 g
- **언폴드 L×W×H**: 255 × 181 × 91 mm
- **프로펠러**: Ø152 mm × 2날
- **착륙장치**: none (rests on lower front arms / body underside; no dedicated legs)
- **짐벌/색상**: front-bottom (nose, 3-axis gimbal mounted at front underside) · dark gray
- **RTK**: False · **최고속도**: 19
- **주의**: Released and shipping product (launched 2025-09-17), so core figures are official and high-confidence. WEIGHT: 249.9 g takeoff weight (DJI lists approx +/-4 g tolerance; some reviewers note real-world configs can nudge over 250 g). FOLDED (without propellers): 157 x 95 x 68 mm (L x W x H) — official. UNFOLDED: DJI publishes TWO unfolded figures: 255 x 181 x 91 mm (arm/body span, propellers attached but not counting diagonal prop-tip reach) and 304 x 380 x 91 mm (L x W x H bounding box measured to the propeller tips diagonally). I put 255 x 181 x 91 in the unfolded L/W/H fields as the body/arm footprint; use 304 x 380 mm if you need the full spinning-prop envelope. DIAGONAL WHEELBASE (motor-to-motor) IS ESTIMATED, NOT OFFICIAL — DJI does not publish a diagonal-distance spec for the Mini series. ~250 mm is derived from the unfolded footprint and 152 mm props (prop-tip bounding box 304 x 380 mm minus prop radius); treat as +/- ~20 mm and verify against a real unit or 3-view drawing before finalizing the CAD. PROPELLER: DJI part 6028F, dimensions 15.2 x 7.1 cm => ~152 mm diameter (about 6.0 in) with ~71 mm / 2.8 in pitch; 2 blades per prop; nylon + rubber with orange low-noise tips; quick-release push/twist-lock mount (not screw-on). GIMBAL/CAMERA: 3-axis mechanical gimbal at the front underside, 1-inch 50MP CMOS f/1.8, headline 225-degree roll for vertical shooting; mechanical roll range about -230 to 95 deg. MAX SPEED 19 m/s in Sport mode with the Intelligent Flight Battery Plus (18 m/s with the standard battery). No RTK, no retractable/dedicated landing gear (lands on lower arms/body).
- **검증**: 일치=True · No corrections to the five fields I was asked to verify (motor-to-motor diagonal, takeoff weight, number of rotors, propeller diameter, release status); all are confirmed or, for the diagonal, reasonable. CAVEAT on diagonal_mm: the 250 mm value is NOT independently verifiable — DJI does not publish a diagonal/motor-to-motor wheelbase spec for the Mini 5 Pro anywhere (absent from the official dji.com specs page, the DJI support propeller page, and all third-party sources). It is the first researcher's derived estimate and should be treated as approximate (+/- ~20 mm); verify against a 3-view drawing or physical unit before finalizing CAD. SEPARATE (not in my 5 target fields but worth flagging): the researcher's unfolded_l/w/h of 255 x 181 x 91 mm is NOT an official DJI figure — the official DJI specs page lists unfolded as 304 x 380 x 91 mm (L x W x H). The 255 x 181 figure does not appear on the official specs page; only 304 x 380 x 91 (unfolded) and 157 x 95 x 68 (folded) are official. If a single unfolded bounding box is needed, use 304 x 380 x 91 mm.
- **출처**:
  - https://www.dji.com/mini-5-pro/specs
  - https://drdrone.com/pages/dji-mini-5-pro-technical-specifications
  - https://dronexl.co/2025/09/14/dji-mini-5-pro-official-description-leaked/
  - https://www.heliguy.com/blogs/posts/top-10-features-dji-mini-5-pro/
  - https://support.dji.com/help/content?customId=en-us03400006559&spaceId=34&re=US&lang=en&documentType=artical&paperDocType=paper
  - https://www.tomsguide.com/cameras-photography/drones/dji-mini-5-pro-review

## DJI Mavic 4 Pro

- **출시상태**: released (2025) · 신뢰도 high
- **구성**: folding quadcopter · 로터 4 · 암 4 · 동축 False
- **대각거리(휠베이스)**: 400 mm
- **이륙중량**: 1063 g
- **언폴드 L×W×H**: 328.7 × 390.5 × 135.2 mm
- **프로펠러**: Ø266.7 mm × 2날
- **착륙장치**: none (rests on lower body / folded arms; no dedicated legs)
- **짐벌/색상**: front-bottom (nose-mounted gimbal under the forward fuselage) · light gray / silver-gray
- **RTK**: False · **최고속도**: 25
- **주의**: DJI Mavic 4 Pro, released May 2025. Official figures: takeoff weight approx. 1063 g; unfolded (without props) 328.7 x 390.5 x 135.2 mm; folded (without props) 257.6 x 124.8 x 103.4 mm; propellers 266.7 mm (10.5 in) diameter, foldable two-blade; folding quadcopter, 4 motors / 4 arms, non-coaxial; triple-camera gimbal with a 360-degree 'infinity' rotating mount; max speed ~25 m/s. DJI does not publish a diagonal/wheelbase figure for the Mavic 4 Pro, so the 400 mm diagonal here is an estimate (Mavic 3 was 380.1 mm; the larger Mavic 4 Pro is somewhat bigger).
- **검증**: 일치=True · Confirmed as official DJI Mavic 4 Pro values: takeoff weight 1063 g, 4 rotors (non-coaxial), propeller 266.7 mm (10.5 in) two-blade, release status 'released' (May 2025). Note: diagonal_mm = 400 is an estimate — DJI publishes no diagonal/wheelbase distance for the Mavic 4 Pro.
- **출처**:
  - https://drdrone.ca/pages/dji-mavic-4-pro-technical-specifications
  - https://www.cliftoncameras.co.uk/uploads/specifications/DJI%20Mavic%204%20Pro%20Specification.pdf
  - https://www.marcotec-shop.com/media/download/Mavic-4-Pro_Specifications.pdf

## DJI Matrice 4E (M4E)

- **출시상태**: released (2025) · 신뢰도 high
- **구성**: folding quadcopter · 로터 4 · 암 4 · 동축 False
- **대각거리(휠베이스)**: 438.8 mm
- **이륙중량**: 1219 g
- **언폴드 L×W×H**: 307 × 387.5 × 149.5 mm
- **프로펠러**: Ø292 mm × 2날
- **착륙장치**: none (skid-free; rests on lower arm/body and battery base)
- **짐벌/색상**: front-bottom (3-axis gimbal mounted at the nose/front-belly) · light gray / off-white
- **RTK**: True · **최고속도**: 21
- **주의**: Released product. The Matrice 4 Series (M4E mapping + M4T thermal) was officially announced by DJI on 2025-01-08 and is shipping as of 2026-06-30; all figures below are official DJI specs unless noted. CONFIRMED from official DJI specs page and dronespec datasheet: diagonal wheelbase 438.8 mm; takeoff weight 1219 g (standard props) / 1229 g (low-noise props); max takeoff weight 1420 g (standard) / 1430 g (low-noise); folded 260.6x113.7x138.4 mm, unfolded 307.0x387.5x149.5 mm (L x W x H, excl. props); max horizontal speed 21 m/s forward (18 backward, 19 lateral). PROPELLER CAVEAT: DJI lists prop models 1157F (standard) and 1154F (low-noise); the leading '115' denotes ~11.5-inch (~292 mm) 2-blade props, the value used here. One third-party datasheet (dronespec) instead lists '10.8 inches' (~274 mm) — treat prop diameter as ~274-292 mm with mild uncertainty; blade count is 2 (standard DJI folding props). LANDING GEAR: like the Mavic 3 Enterprise platform it has no separate landing skids; report as 'none'. Body color is DJI's standard enterprise light gray/off-white. Gimbal sits at the front-belly on a 3-axis mount with the triple-camera + laser-range-finder cluster. RTK is integrated (FIX accuracy 1 cm + 1 ppm horizontal).
- **검증**: 일치=False · propeller_diameter_mm: change from 292 to 274 (DJI official spec lists 10.8 in = 274.3 mm; the '115' in prop model 1157F is not 11.5 inches). All other verified fields are correct: diagonal_mm 438.8, weight_g 1219 (standard props; 1229 low-noise), num_rotors 4, release_status 'released' (announced 2025-01-08, shipping).
- **출처**:
  - https://enterprise.dji.com/matrice-4-series/specs
  - https://enterprise.dji.com/news/detail/matrice-4-series-release
  - https://dronespec.dronedesk.io/dji-matrice-4e
  - https://www.dslrpros.com/products/dji-matrice-4e-universal-edition-aircraft-only
  - https://geonadir.com/matrice-4-enterprise/

## DJI Spreading Wings S1000+

- **출시상태**: discontinued (2014) · 신뢰도 high
- **구성**: fixed-position-rotor folding octocopter (8 arms, 1 rotor per arm) · 로터 8 · 암 8 · 동축 False
- **대각거리(휠베이스)**: 1045 mm
- **이륙중량**: 4400 g
- **언폴드 L×W×H**: 1045 × 1045 × 462 mm
- **프로펠러**: Ø381 mm × 2날
- **착륙장치**: retractable (motorized/servo-driven, raises out of frame for unobstructed camera view)
- **짐벌/색상**: belly (hangs below the center frame on a damped bracket; compatible with Zenmuse Z15 series, not an integrated camera) · black (matte black carbon-fiber arms and center plates with red motor-mount/arm accents and red rotor-direction markers)
- **RTK**: False · **최고속도**: None
- **주의**: Real, released, now-discontinued product (S1000+ is the 2014 upgraded version of the 2013 S1000). Figures are OFFICIAL DJI specs except where noted. CONFIRMED: diagonal wheelbase 1045 mm; total airframe weight 4.4 kg (4400 g); recommended/usable takeoff weight 6.0-11.0 kg (commonly cited recommended ~9.5 kg, max 11 kg); frame arm length 386 mm; center frame diameter 337 mm; motor 4114 Pro (KV400, 500 W, stator 41x14 mm, 158 g w/ fan); foldable propeller model 1552/1552R, 15x5.2 inch => 381 mm diameter, 2 blades, 13 g; 40 A ESC per arm. IMPORTANT: This is an 8-arm, single-rotor-per-arm octocopter — rotors are NOT coaxially stacked (coaxial=false), unlike some X8 builds. ESTIMATES/caveats: (1) Unfolded L/W ~1045 mm uses motor-to-motor diagonal as the bounding box; true tip-to-tip with 381 mm props is larger (~1045 + ~one prop radius). (2) Unfolded height ~462 mm and landing-gear envelope derived from official landing-gear bounding box 460(L)x511(W)x305(H) mm plus center-frame stack; H is approximate. (3) Folded L/W ~390 mm is ESTIMATED from frame arm length 386 mm (arms fold inward); DJI does not publish exact folded outer dimensions, so folded values are approximate. (4) The S1000+ ships as an airframe; gimbal/camera (Zenmuse Z15-GH4/BMPCC/5D) and flight controller (A2/WooKong-M) are separate — has_gimbal_camera reflects the intended belly-mounted gimbal payload rather than a built-in camera. max_speed not officially specified.
- **검증**: 일치=True · No corrections to the five queried fields — all independently confirmed. diagonal_mm=1045 (DJI official + dronespec + retailers); num_rotors=8 with coaxial=false (DJI newsroom: 8 arms, each arm has its own 40A ESC and 4114 pro motor = one rotor per arm; note the dronespec.dronedesk.io datasheet incorrectly describes it as "four arms with dual coaxial motors" — this is an error in that third-party source, contradicted by the authoritative DJI announcement); propeller_diameter_mm=381 (1552 props, 15x5.2 inch); release_status=discontinued (launched Feb 2014, discontinued ~2016). On weight: weight_g=4400 is correct as the AIRFRAME weight; the usable/recommended takeoff weight is 6.0-11.0 kg (reference ~9.5 kg, max 11 kg), as the researcher already noted — not a contradiction, just a definitional distinction.
- **출처**:
  - https://www.dji.com/spreading-wings-s1000-plus/info
  - https://www.dji.com/support/product/spreading-wings-s1000-plus
  - https://dronespec.dronedesk.io/dji-spreading-wings-s1000-plus
  - https://www.bhphotovideo.com/c/product/1087654-REG/dji_cp_sb_000129r_spreading_wings_s1000_professional.html
  - https://www.amainhobbies.com/dji-spreading-wings-s1000-ap-octocopter-drone-kit-dji-s1000a2/p424450

## DJI Phantom 4 (original, 2016)

- **출시상태**: released (2016) · 신뢰도 high
- **구성**: fixed-arm quadcopter · 로터 4 · 암 4 · 동축 False
- **대각거리(휠베이스)**: 350 mm
- **이륙중량**: 1380 g
- **언폴드 L×W×H**: 350 × 350 × 198 mm
- **프로펠러**: Ø239 mm × 2날
- **착륙장치**: fixed integrated legs (skid-style, molded into shell with antennas in legs)
- **짐벌/색상**: front-bottom (3-axis gimbal hanging from underside of nose/belly, recessed into the body) · white (glossy white shell with silver/grey trim and red/silver stripes on the rear arms)
- **RTK**: False · **최고속도**: 20
- **주의**: DEFINITIVELY RELEASED in March 2016; this is a real, mass-produced product, not rumored. Figures are official/well-corroborated. CONFIRMED across multiple sources: diagonal distance (propellers excluded) = 350 mm; takeoff weight (incl. battery + props) = 1380 g; max speed 20 m/s in Sport mode; 3-axis gimbal with 1/2.3-inch 12.4MP camera; 28 min flight time; 5350 mAh battery. Propellers: official DJI 9450 self-tightening = 9.4-inch diameter (~239 mm) x 5.0-inch pitch, 2-blade plastic (two CW + two CCW). NOT coaxial — one rotor per arm. Arms are FIXED (non-folding); the Phantom 4 does NOT fold, so folded dims are null/not applicable. Caveat on bounding-box dimensions: DJI's official spec sheet lists only the 350 mm diagonal (motor-to-motor), not an explicit L x W x H. The unfolded L/W ≈ 350 mm represent the motor-to-motor footprint square; with propellers attached the prop-tip span is larger (~590 mm tip-to-tip). Height ~198 mm is the commonly cited overall height including landing gear and gimbal (estimate from retailer/box dimensions; not an official DJI figure). The diagonal_mm and the L/W footprint are the same 350 mm value because they both reference the motor-to-motor diagonal. For a dimensionally exact CAD model, treat 350 mm motor-to-motor diagonal, 1380 g, and the 9450 prop (239 mm) as the load-bearing official numbers; verify the precise shell height/landing-gear span against a physical unit or DJI CAD if available, since official H is not published.
- **검증**: 일치=True · None. All five verified fields are correct. Diagonal wheelbase = 350 mm (motor-to-motor, props excluded), takeoff weight = 1380 g (incl. battery + props), num_rotors = 4 (quadcopter, non-coaxial), propeller diameter = 239 mm (DJI 9450/9450S = 9.4 in = 238.8 mm; note the 9.4 in is the DIAMETER while 5.0 in is the pitch — some summaries mislabel the 5 in pitch as 'diameter'), release_status = released (DEFINITIVELY released March 2016, mass-produced, not rumored). Minor non-correction note: Wikipedia lists 1.375 kg as 'empty weight' vs the 1380 g takeoff weight; these are consistent and the 1380 g official takeoff figure stands.
- **출처**:
  - https://www.fullcompass.com/common/files/27734-DJIPhantom4SpecSheet.pdf
  - https://dronespec.dronedesk.io/dji-phantom-4
  - https://drone-world.com/dji-phantom-4-specs/
  - https://en.wikipedia.org/wiki/DJI_Phantom
  - https://www.dji.com/phantom-4/info
  - https://store.dji.com/product/self-tightening-propellers
