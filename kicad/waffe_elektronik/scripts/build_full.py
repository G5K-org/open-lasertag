#!/usr/bin/env python3
import sys
sys.path.insert(0, ".")
from build_sch import Sheet, place_module

DEV = "/usr/share/kicad/symbols/Device.kicad_sym"
DIODE = "/usr/share/kicad/symbols/Diode.kicad_sym"
FET = "/usr/share/kicad/symbols/Transistor_FET.kicad_sym"
SWITCH = "/usr/share/kicad/symbols/Switch.kicad_sym"
MOTOR = "/usr/share/kicad/symbols/Motor.kicad_sym"
CONN = "/usr/share/kicad/symbols/Connector_Generic.kicad_sym"
AUDIO = "/usr/share/kicad/symbols/Audio.kicad_sym"
OPTICAL = "/usr/share/kicad/symbols/Interface_Optical.kicad_sym"
POWER = "/usr/share/kicad/symbols/power.kicad_sym"
BATTMGMT = "/usr/share/kicad/symbols/Battery_Management.kicad_sym"
REGLIN = "/usr/share/kicad/symbols/Regulator_Linear.kicad_sym"
LOGIC74 = "/usr/share/kicad/symbols/74xx.kicad_sym"

sh = Sheet()

def R(value, x, y, angle=0):
    return sh.place(DEV, "R", "Device", "R", value, x, y, angle=angle)

def C(value, x, y, polarized=False):
    entry = "C_Polarized" if polarized else "C"
    return sh.place(DEV, entry, "Device", "C", value, x, y)

def LED(x, y, angle=0):
    return sh.place(DEV, "LED", "Device", "LED", "TSAL6100", x, y, angle=angle)

def NMOS(x, y, value="AO3400A"):
    return sh.place(FET, "AO3400A", "Transistor_FET", "Q", value, x, y)

def DIO(x, y, value="SS14"):
    return sh.place(DIODE, "SS14", "Diode", "D", value, x, y)

def SW(x, y):
    return sh.place(SWITCH, "SW_Push", "Switch", "SW", "Taster", x, y)

def MOT(x, y, value="Vibromotor"):
    return sh.place(MOTOR, "Motor_DC", "Motor", "M", value, x, y)

def BATT(x, y):
    return sh.place(DEV, "Battery_Cell", "Device", "BT", "1S LiPo 3.7V", x, y)

def TSOP(x, y):
    return sh.place(OPTICAL, "TSOP348xx", "Interface_Optical", "U", "TSOP34838", x, y)

def MCP(x, y):
    return sh.place(BATTMGMT, "MCP73831-2-OT", "Battery_Management", "U", "MCP73831", x, y)

def MAX(x, y):
    return sh.place(AUDIO, "MAX98357A", "Audio", "U", "MAX98357A", x, y)

def LDO(x, y):
    return sh.place(REGLIN, "AMS1117-3.3", "Regulator_Linear", "U", "AMS1117-3.3", x, y)

def BUF74(x, y, unit):
    return sh.place(LOGIC74, "74AHCT125", "74xx", "U", "74AHCT125", x, y, unit=unit, ref_override="U_LVLSHIFT" if unit != 1 else None)

def GX(n, x, y):
    return sh.place(CONN, f"Conn_01x{n:02d}", "Connector_Generic", "J", f"GX16-{n}pol", x, y)

def SPK(x, y):
    return sh.place(DEV, "Speaker", "Device", "SP", "Lautsprecher", x, y)

def PWRFLAG(x, y, net):
    _, pf = sh.place(POWER, "PWR_FLAG", "power", "#FLG", "PWR_FLAG", x, y, angle=90)
    sh.net(pf["1"], net)


# ========================= POWER SECTION =========================
sh.text("STROMVERSORGUNG", 20, 30, size=2.5)

_, bt = BATT(20, 60)
sh.net(bt["+"], "BAT_P")
sh.net(bt["-"], "GND")

# 5V boost converter (generic MT3608-style module) battery -> 5V_PERIPH
_, boost = place_module(sh, "Module", "Boost_5V_MT3608", [("IN+", "1"), ("IN-", "2")], [("OUT+", "3"), ("OUT-", "4")], "U", 45, 60)
sh.net(boost["IN+"], "BAT_P")
sh.net(boost["IN-"], "GND")
sh.net(boost["OUT+"], "5V_PERIPH")
sh.net(boost["OUT-"], "GND")

_, c_boost = C("220u", 65, 60, polarized=True)
sh.net(c_boost["1"], "5V_PERIPH")
sh.net(c_boost["2"], "GND")

# LDO 5V_PERIPH -> 3V3_MCU (feeds the DevKitC's 3V3 pin directly, bypassing its own 5V-input LDO)
_, ldo = LDO(85, 60)
sh.net(ldo["VI"], "5V_PERIPH")
sh.net(ldo["GND"], "GND")
sh.net(ldo["VO"], "3V3_MCU")

_, c_ldo_in = C("10u", 80, 48, polarized=True)
sh.net(c_ldo_in["1"], "5V_PERIPH")
sh.net(c_ldo_in["2"], "GND")
_, c_ldo_out = C("10u", 92, 48, polarized=True)
sh.net(c_ldo_out["1"], "3V3_MCU")
sh.net(c_ldo_out["2"], "GND")

# Charger: fed ONLY from the MCU module's native VBUS pin (no boost/battery feedback)
_, chg = MCP(20, 100)
sh.net(chg["V_{SS}"], "GND")
sh.net(chg["V_{BAT}"], "BAT_P")
sh.net(chg["V_{DD}"], "VBUS_NATIVE")
sh.net(chg["STAT"], "CHRG_STAT")

_, r_prog = R("2k", 10, 110, angle=90)
sh.net(r_prog["1"], "GND")
sh.net(r_prog["2"], "PROG")
sh.net(chg["PROG"], "PROG")

_, r_stat = R("10k", 35, 90, angle=90)
sh.net(r_stat["1"], "3V3_MCU")
sh.net(r_stat["2"], "CHRG_STAT")

_, c_chg_in = C("1u", 30, 100)
sh.net(c_chg_in["1"], "VBUS_NATIVE")
sh.net(c_chg_in["2"], "GND")
_, c_chg_bat = C("1u", 40, 100)
sh.net(c_chg_bat["1"], "BAT_P")
sh.net(c_chg_bat["2"], "GND")

# Battery voltage divider for ADC (4.2V max -> ~2.1V)
_, rdiv1 = R("100k", 20, 130, angle=90)
sh.net(rdiv1["1"], "BAT_P")
sh.net(rdiv1["2"], "ADC_BATT")
_, rdiv2 = R("100k", 20, 145, angle=90)
sh.net(rdiv2["1"], "ADC_BATT")
sh.net(rdiv2["2"], "GND")
_, c_adc = C("100n", 30, 138)
sh.net(c_adc["1"], "ADC_BATT")
sh.net(c_adc["2"], "GND")

PWRFLAG(60, 75, "GND")
PWRFLAG(100, 75, "5V_PERIPH")
PWRFLAG(15, 90, "VBUS_NATIVE")

sh.text("5V_PERIPH speist WS2812 + MAX98357A + 74AHCT125.", 20, 155, size=1.3)
sh.text("3V3_MCU speist NUR das MCU-3V3-Pin (DevKitC-eigene", 20, 158, size=1.3)
sh.text("5V->3V3-LDO wird dadurch bewusst nicht genutzt).", 20, 161, size=1.3)
sh.text("VBUS_NATIVE = eigener USB-C-Port der Waffe (Flash-Port),", 20, 164, size=1.3)
sh.text("nur fuer den Lader - keine Rueckspeisung aus Boost/Akku.", 20, 167, size=1.3)

# ========================= MCU MODULE =========================
MCU_LEFT = [
    ("GPIO1_SPARE", "GPIO1"), ("GPIO2_SPARE", "GPIO2"), ("IR_GATE", "GPIO4"),
    ("TRIGGER", "GPIO5"), ("RELOAD", "GPIO6"), ("RECOIL_VIB", "GPIO7"),
    ("ADC_BATT", "GPIO8"), ("HIT_VIB", "GPIO11"), ("TSOP1_OUT", "GPIO12"),
    ("TSOP2_OUT", "GPIO13"), ("TSOP3_OUT", "GPIO14"), ("TSOP4_OUT", "GPIO15"),
    ("TSOP5_OUT", "GPIO16"), ("WS2812_DIN_3V3", "GPIO17"), ("CHRG_STAT", "GPIO18"),
    ("I2S_BCLK", "GPIO21"), ("I2S_LRCLK", "GPIO38"), ("I2S_DOUT", "GPIO39"),
]
MCU_RIGHT = [("3V3_MCU", "3V3"), ("GND", "GND1"), ("GND", "GND2"), ("VBUS_NATIVE", "VBUS")]

sh.text("WAFFE - ESP32-S3-DevKitC-1 (Hauptplatine)", 100, 30, size=2.5)
_, mcu = place_module(sh, "Module", "ESP32S3_DevKitC", MCU_LEFT, MCU_RIGHT, "U", 130, 140)
for net_name, pin_num in MCU_LEFT:
    sh.net(mcu[pin_num], net_name)
for net_name, pin_num in MCU_RIGHT:
    sh.net(mcu[pin_num], net_name)

# ========================= IR-LED TREIBER (Waffe) =========================
sh.text("IR-SENDER", 170, 30, size=2.5)

_, q_ir = NMOS(180, 60)
sh.net(q_ir["G"], "IR_GATE_FET")
sh.net(q_ir["S"], "GND")
sh.net(q_ir["D"], "IR_K")

_, r_ir_gate = R("100", 170, 60, angle=90)
sh.net(r_ir_gate["1"], "IR_GATE")       # from MCU GPIO4
sh.net(r_ir_gate["2"], "IR_GATE_FET")   # to MOSFET gate

_, r_ir_pulldown = R("100k", 175, 50, angle=90)
sh.net(r_ir_pulldown["1"], "IR_GATE_FET")
sh.net(r_ir_pulldown["2"], "GND")

_, led1 = LED(200, 50, angle=180)
sh.net(led1["A"], "IR_LED_ANODE1")
sh.net(led1["K"], "IR_K")
_, r_led1 = R("10", 210, 50, angle=90)
sh.net(r_led1["1"], "BAT_P")
sh.net(r_led1["2"], "IR_LED_ANODE1")

_, led2 = LED(200, 65, angle=180)
sh.net(led2["A"], "IR_LED_ANODE2")
sh.net(led2["K"], "IR_K")
_, r_led2 = R("10", 210, 65, angle=90)
sh.net(r_led2["1"], "BAT_P")
sh.net(r_led2["2"], "IR_LED_ANODE2")

_, c_ir_bulk = C("220u", 190, 60, polarized=True)
sh.net(c_ir_bulk["1"], "BAT_P")
sh.net(c_ir_bulk["2"], "IR_K")

sh.text("2x TSAL6100 parallel, je eigener Vorwiderstand (readme.md Abschnitt 4).", 170, 80, size=1.3)

# ========================= ABZUG / NACHLADEN =========================
sh.text("ABZUG / NACHLADEN", 170, 100, size=2.5)

_, sw_trig = SW(180, 120)
sh.net(sw_trig["1"], "TRIGGER")
sh.net(sw_trig["2"], "GND")
_, r_trig_pu = R("10k", 180, 108, angle=90)
sh.net(r_trig_pu["1"], "3V3_MCU")
sh.net(r_trig_pu["2"], "TRIGGER")
_, c_trig = C("100n", 190, 120)
sh.net(c_trig["1"], "TRIGGER")
sh.net(c_trig["2"], "GND")

_, sw_reload = SW(180, 140)
sh.net(sw_reload["1"], "RELOAD")
sh.net(sw_reload["2"], "GND")
_, r_reload_pu = R("10k", 180, 128, angle=90)
sh.net(r_reload_pu["1"], "3V3_MCU")
sh.net(r_reload_pu["2"], "RELOAD")
_, c_reload = C("100n", 190, 140)
sh.net(c_reload["1"], "RELOAD")
sh.net(c_reload["2"], "GND")

# ========================= VIBRATIONSMOTOREN =========================
sh.text("RUECKSTOSS- / TREFFER-VIBRATION", 170, 160, size=2.5)

_, q_recoil = NMOS(180, 185)
sh.net(q_recoil["G"], "RECOIL_VIB_FET")
sh.net(q_recoil["S"], "GND")
sh.net(q_recoil["D"], "RECOIL_M_MINUS")
_, r_recoil_gate = R("100", 170, 185, angle=90)
sh.net(r_recoil_gate["1"], "RECOIL_VIB")       # from MCU GPIO7
sh.net(r_recoil_gate["2"], "RECOIL_VIB_FET")   # to MOSFET gate
_, r_recoil_pulldown = R("100k", 165, 185, angle=90)
sh.net(r_recoil_pulldown["1"], "RECOIL_VIB_FET")
sh.net(r_recoil_pulldown["2"], "GND")
_, m_recoil = MOT(200, 180, "Vibromotor Rueckstoß")
sh.net(m_recoil["+"], "5V_PERIPH")
sh.net(m_recoil["-"], "RECOIL_M_MINUS")
_, d_recoil = DIO(210, 185, "SS14")
sh.net(d_recoil["K"], "5V_PERIPH")
sh.net(d_recoil["A"], "RECOIL_M_MINUS")

_, q_hit = NMOS(180, 210)
sh.net(q_hit["G"], "HIT_VIB_FET")
sh.net(q_hit["S"], "GND")
sh.net(q_hit["D"], "HIT_M_MINUS")
_, r_hit_gate = R("100", 170, 210, angle=90)
sh.net(r_hit_gate["1"], "HIT_VIB")       # from MCU GPIO11
sh.net(r_hit_gate["2"], "HIT_VIB_FET")   # to MOSFET gate
_, r_hit_pulldown = R("100k", 165, 210, angle=90)
sh.net(r_hit_pulldown["1"], "HIT_VIB_FET")
sh.net(r_hit_pulldown["2"], "GND")
_, m_hit = MOT(200, 205, "Vibromotor Treffer")
sh.net(m_hit["+"], "5V_PERIPH")
sh.net(m_hit["-"], "HIT_M_MINUS")
_, d_hit = DIO(210, 210, "SS14")
sh.net(d_hit["K"], "5V_PERIPH")
sh.net(d_hit["A"], "HIT_M_MINUS")

# ========================= PEGELWANDLER + WS2812 =========================
sh.text("WS2812 (5V) UEBER PEGELWANDLER", 230, 30, size=2.5)

ref_buf, buf1 = sh.place(LOGIC74, "74AHCT125", "74xx", "U", "74AHCT125", 240, 60, unit=1)
_, buf5 = sh.place(LOGIC74, "74AHCT125", "74xx", "U", "74AHCT125", 240, 60, unit=5, ref_override=ref_buf)
sh.net(buf1["1"], "GND")          # 1OE tied low -> gate always enabled
sh.net(buf1["2"], "WS2812_DIN_3V3")  # 1A, from MCU GPIO17
sh.net(buf1["3"], "WS2812_DIN_5V")   # 1Y
sh.net(buf5["7"], "GND")
sh.net(buf5["14"], "5V_PERIPH")

_, r_ws_series = R("330", 250, 60, angle=90)
sh.net(r_ws_series["1"], "WS2812_DIN_5V")
sh.net(r_ws_series["2"], "WS2812_HP_DIN")

_, j_ws_hp = sh.place(CONN, "Conn_01x03", "Connector_Generic", "J", "WS2812 HP-Streifen", 265, 60)
sh.net(j_ws_hp["1"], "WS2812_HP_DIN")
sh.net(j_ws_hp["2"], "5V_PERIPH")
sh.net(j_ws_hp["3"], "GND")

_, c_ws_hp = C("470u", 275, 60, polarized=True)
sh.net(c_ws_hp["1"], "5V_PERIPH")
sh.net(c_ws_hp["2"], "GND")

sh.text("Munitionsanzeige haengt als weitere WS2812-Pixel am physischen", 230, 90, size=1.3)
sh.text("DOUT-Pin des HP-Streifens (Daisy-Chain, hier nicht separat", 230, 93, size=1.3)
sh.text("dargestellt) - GPIO1/GPIO2 bleiben dadurch frei.", 230, 96, size=1.3)
sh.text("Falls OLED statt LED-Zeile gewuenscht: GPIO1/2 als I2C nutzen.", 230, 99, size=1.3)

# ========================= AUDIO =========================
sh.text("SOUND", 230, 115, size=2.5)

_, amp = MAX(240, 150)
sh.net(amp["DIN"], "I2S_DOUT")
sh.net(amp["LRCLK"], "I2S_LRCLK")
sh.net(amp["BCLK"], "I2S_BCLK")
sh.net(amp["GAIN_SLOT"], "GND")
sh.net(amp["~{SD_MODE}"], "5V_PERIPH")
sh.net(amp["VDD"], "5V_PERIPH")
sh.net(amp["GND"], "GND")
sh.net(amp["PAD"], "GND")

_, spk = SPK(270, 150)
sh.net(spk["1"], "SPK_OUTP")
sh.net(spk["2"], "SPK_OUTN")
sh.net(amp["OUTP"], "SPK_OUTP")
sh.net(amp["OUTN"], "SPK_OUTN")

sh.text("SD_MODE fest auf 5V_PERIPH (immer aktiv), GAIN_SLOT auf GND", 230, 165, size=1.3)
sh.text("(Standard-Gain) - siehe pinbelegung.md offene Fragen.", 230, 168, size=1.3)

# ========================= SENSORKABEL + WESTE =========================
sh.text("SENSORKABEL ZUR WESTE (GX12/GX16, 7-polig)", 20, 230, size=2.5)

_, j_sensor = GX(7, 60, 260)
sh.net(j_sensor["1"], "3V3_MCU")
sh.net(j_sensor["2"], "GND")
sh.net(j_sensor["3"], "TSOP1_OUT")
sh.net(j_sensor["4"], "TSOP2_OUT")
sh.net(j_sensor["5"], "TSOP3_OUT")
sh.net(j_sensor["6"], "TSOP4_OUT")
sh.net(j_sensor["7"], "TSOP5_OUT")

sh.text("WESTE (jenseits des Steckers, nur Sensoren, kein Chip)", 20, 280, size=2.0)
tsop_nets = ["TSOP1_OUT", "TSOP2_OUT", "TSOP3_OUT", "TSOP4_OUT", "TSOP5_OUT"]
tsop_labels = ["Stirnband vorn", "Stirnband hinten", "Brust", "Ruecken", "Schultern"]
for i, (net, label) in enumerate(zip(tsop_nets, tsop_labels)):
    yy = 300 + i * 25
    local_net = f"TSOP{i+1}_VCC"
    _, tsop = TSOP(40, yy)
    sh.net(tsop["Vs"], local_net)
    sh.net(tsop["GND"], "GND")
    sh.net(tsop["OUT"], net)
    _, r_tsop = R("100", 30, yy - 8, angle=90)
    sh.net(r_tsop["1"], "3V3_MCU")
    sh.net(r_tsop["2"], local_net)
    _, c_tsop = C("4.7u", 30, yy, polarized=True)
    sh.net(c_tsop["1"], local_net)
    sh.net(c_tsop["2"], "GND")
    PWRFLAG(45, yy - 15, local_net)
    sh.text(label, 50, yy, size=1.3)

sh.finalize_nets()

import os
out = os.environ.get("OUT_SCH", "test_full_stage3.kicad_sch")
sh.save(out)
print("stage3 ok ->", out)
