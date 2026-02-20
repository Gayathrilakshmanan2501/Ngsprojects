import random
import sounddevice as sd
import json
from gpiozero import LED
from time import sleep
import re
import subprocess
from datetime import datetime, timedelta
from vosk import Model, KaldiRecognizer
import time
import os
import threading
import osmnx as ox
import networkx as nx
import math
import board
import adafruit_dht
import csv


navigation_instructions=[]
current_step_index=0
navigation_active= False
alarm_process = None
stop_story_flag = False
alarm_setting = False
waiting_for_diary=False
stop_timer_flag= False
dictionary = {}
timers=[]
alarms=[]
ALARM_SOUND="alarm.wav"
wait_for_alarm = False
wait_for_snooze = False
current_alarm = None
alarm_playing = False
music_process=None #from line 105
dhtDevice = adafruit_dht.DHT11(board.D4)

led = LED(18)   # change if you use another pin

def load_hindi_gk():
    try:
        with open("hindi_gk.json", "r", encoding="utf-8") as f:
            hindi_gk = json.load(f)  # Load the content from the JSON file
        return hindi_gk
    except FileNotFoundError:
        print("hindi_gk.json file not found.")
        return {}
    except json.JSONDecodeError:
        print("Error decoding the JSON file.")
        return {}

hindi_gk = load_hindi_gk()  # Load the GK data from the JSON file
WAKE_WORD = "नमस्ते"
SLEEP_WORDS = ["सो जाओ", "चुप हो जाओ", "बाय", "आराम करो"]
active_until = 0 # timestamp till which assistant stays active
ACTIVE_WINDOW = 60 #15 seconds conversation mode
REM_FILE = "reminders.json"
DIARY_FILE = "voice_diary.json"
wait_min = False
hindi_number_map = {"शून्य": 0,"एक": 1,"दो": 2,"तीन": 3,"चार": 4,"पाँच": 5,
"छह": 6,"सात": 7,"आठ": 8,"नौ": 9,"दस":10,"ग्यारह": 11,"बारह": 12,"तेरह": 13,
"चौदह": 14,"पंद्रह": 15,"सोलह": 16,"सत्रह": 17,"अट्ठारह": 18,"उन्नीस": 19,
"बीस": 20,"इक्कीस": 21,"बाईस": 22,"तेइस": 23,"चौबीस": 24,"पच्चीस": 25,"छब्बीस": 26,"सत्ताईस": 27,
"अट्ठाईस": 28,"उनतीस": 29,"तीस": 30,"इकतीस": 31,"बत्तीस": 32,"तेतीस": 33,"चौंतीस": 34,
"पैंतीस": 35,"छतीस": 36,"सैंतीस": 37,"अड़तीस": 38,"उनतालीस": 39,"चालीस": 40,"इकतालीस": 41,
"बयालीस": 42,"तैंतालीस": 43,"चवालीस": 44,"पैंतालीस": 45,"छियालीस": 46,"सैंतालीस": 47,
"अड़तालीस": 48,"उनचास": 49,"पचास": 50,"इक्यावन": 51,"बावन": 52,"त्रिपन": 53,"चौवन": 54,"पचपन": 55,"छप्पन": 56,"सत्तावन": 57,"अट्ठावन": 58,"उनसठ": 59
}

INTENTS = {
    "samay": ["समय"],
    "date": ["तारीख"],
    "play_song": ["गाना", "म्यूजिक चलाओ"],
    "change_song": ["गाना बदलो", "अगला गाना", "दूसरा गाना", "नेक्स्ट सॉन्ग"],
    "stop_song": ["गाना बंद","म्यूजिक बंद"],
    "alarm": ["अलार्म","अलार्म घड़ी लगाओ", "घड़ी लगाओ","alarm लगाओ"],
    "timer": ["टाइमर", "के लिए"], #"मिनट"
    "stop_timer": ["रुको","टाइमर रोक"],
    "calculator": ["प्लस", "जोड़", "माइनस", "घटाओ","गुणा","गुना", "भाग", "कैलकुलेटर"],
    "joke": ["जोक", "मजाक", "हंसा दो", "कुछ फनी", "एक लाइन का जोक"],
    "positive" : ["कुछ अच्छा बोलो","पॉजिटिव बोलो","मोटिवेट करो","अच्छी बात"],
    "tongue_twister": ["टंग ट्विस्टर", "मुश्किल बोल", "तेज़ बोल", "जल्दी बोल"],
    "riddle": ["पहेली", "बूझो तो जानो", "एक पहेली पूछो","दिमागी सवाल"],
    "voice_diary": ["डायरी लिखो","डायरी बनाओ","मेरी डायरी","आज की डायरी"],
    "read_diary": ["डायरी सुनाओ","मेरी डायरी पढ़ो","आज की डायरी पढ़ो"],
    "temperature": ["तापमान","टेम्परेचर","गर्मी कितनी है","ठंड कितनी है","मौसम कैसा है"],
    "led_on": ["लाइट चालू", "एलईडी चालू", "लाइट ऑन", "बत्ती जलाओ"],
    "led_off": ["लाइट ऑफ","लाइट आप", "लाइट बुझा दो "],
    "alarm_stop": ["रहने दो","खत्म","अलार्म घड़ी खत्म करो"],
    "alarm_snooze": ["स्थगित","अलार्म घड़ी स्नूज् करो", "snooze अलार्म", "अलार्म बाद में बजाओ"],
    "dictionary" : ["मतलब","अर्थ","translate","translation","meaning","meaning of","का मतलब","का अर्थ"],
    "tell_story": ["कहानी सुनाओ","एक कहानी सुनाओ","कोई कहानी सुनाओ","नैतिक कहानी सुनाओ","मुझे कहानी सुननी है","कहानी बताओ"],
    "stop_story": ["बस करो"],
    "gk_question": ["कौन है", "क्या है", "कहाँ है", "सबसे", "पहला", "राष्ट्रीय", "भारत का", "किस राज्य में"],
    "navigate": ["जाना है", "ले चलो", "रास्ता बताओ", "मार्ग बताओ"],
    "next_step": ["अगला", "नेक्स्ट"],
}

operator_map = {
    "प्लस": "+",
    "जोड़": "+",
    "माइनस": "-",
    "घटाओ": "-",
    "गुणा": "*",
    "गुना": "*",
    "भाग": "/"
}
JOKES = [
    "ज़िंदगी वही है जहाँ WiFi strong हो",
    "पढ़ाई और नींद में एक ही फर्क है – नींद पूरी हो जाती है",
    "आजकल रिश्ते भी WiFi जैसे हैं, पास हो तो कनेक्ट",
    "मेरा दिमाग CPU जैसा है, ज़्यादा सोचो तो hang हो जाता है ",
    "कैलकुलेटर भी मुझसे ज़्यादा तेज़ गणित करता है",
    "मैं diet पर हूँ… बस खाना देखते ही भूल जाता हूँ",
    "मोबाइल गिरते ही इंसान की धड़कन बढ़ जाती है"
]
POSITIVE_LINES = [
    "आज का दिन आपका है",
    "थोड़ी सी मुस्कान बहुत कुछ बदल सकती है",
    "आप जैसा कोई नहीं, और यही खास है",
    "धीरे चलो, लेकिन रुको मत"
]

TONGUE_TWISTERS = [
    "चंदू के चाचा ने चंदू की चटनी चटाई",
    "खड़क सिंह के खड़कने से खड़कती हैं खिड़कियाँ",
    "डबल बबल गम बबल डबल"
]
RIDDLES = [
    "ऐसी कौन सी चीज़ है जो बोलती नहीं, फिर भी सब कुछ कह देती है? जवाब: किताब ",
    "वो क्या है जो जितना सुखाओ उतना गीला होता जाता है? जवाब: तौलिया ",
    "ऐसी कौन सी चीज़ है जो आपके पास है लेकिन ज़्यादातर लोग इस्तेमाल करते हैं? जवाब: नाम "
]

MUSIC_FOLDER = "/home/srinidhi2/vosk_env/Music"


SONGS = {
    "केसरि":"kesariya.mpeg",
    "तेरे बिना": "tere_bina.mpeg",
    "jab tak": "jab_tak.mpeg",
    "जब तक": "jab_tak.mpeg",
}

song_keys = list(SONGS.keys())
current_song_index = -1

with open("hindi_dictionary.json","r",encoding="utf-8") as f:
	hindi_dict=json.load(f)
'''with open ("eng_to_hi_translit.json","r",encoding="utf-8") as f1:
	eng_map=json.load(f1)'''


if not os.path.exists(REM_FILE):
    with open(REM_FILE, "w") as f:
        json.dump([], f)
        
def speak(text):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {text}")
    subprocess.run(["espeak-ng", "-v", "hi", text])
    #time.sleep(0.3)

def recognize_intent(text):
    for intent, words in INTENTS.items():
        for w in words:
            if w in text:
                return intent
    return "unknown"
'''
def recognize_intent(text):
    text_words = text.lower().split()   # split into words
    for intent, keywords in INTENTS.items():
        for keyword in keywords:
            keyword_words = keyword.lower().split()
            # check if all words in keyword appear in text in the same order
            for i in range(len(text_words) - len(keyword_words) + 1):
                if text_words[i:i+len(keyword_words)] == keyword_words:
                    return intent
    return "unknown"
'''
def speak_number_in_hindi(n):
    for key, value in hindi_number_map.items():
        if value == n:
            return key
    return str(n)  # fallback, though now all 0–59 are covered
    
def parse_hindi_time(text):
    """
    Examples handled:
    - सात बजे तीस मिनट
    - सात बजे तीस
    - सात बजे 30 मिनट
    - 7 बजे 30
    """
    words = text.split()

    hour = None
    minute = 0

    for i, w in enumerate(words):

        # ----- HOUR -----
        if w.isdigit():
            num = int(w)
        elif w in hindi_number_map:
            num = hindi_number_map[w]
        else:
            num = None

        if num is not None:
            # if next word is 'बजे', it's hour
            if i + 1 < len(words) and words[i + 1] == "बजे":
                hour = num
            # otherwise could be minutes
            elif minute == 0:
                minute = num

    if hour is None:
        return None

    if hour == 12:
        hour = 0

    now = datetime.now()
    alarm_time = now.replace(hour=hour, minute=minute, second=0)

    # if time already passed today → tomorrow
    if alarm_time <= now:
        alarm_time += timedelta(days=1)

    return alarm_time

def normalize(text):
    if text is None:
        return ""
    text = re.sub(r"[^\w\s]", "", text)  # remove punctuation
    text = re.sub(r"\s+", "", text)      # remove spaces
    return text
    
def play_alarm(alarm_time):
    global current_alarm, alarm_playing, alarm_process

    current_alarm = alarm_time
    alarm_playing = True

    #speak("अलार्म बज रहा है")
    #speak("अलार्म बज रहा है")

    while alarm_playing:
        alarm_process = subprocess.Popen(
            ["aplay", ALARM_SOUND],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        alarm_process.wait()
def stop_alarm():
    global current_alarm, alarm_playing, alarm_process

    if alarm_playing:
        alarm_playing = False

        if alarm_process:
            alarm_process.kill()
            alarm_process = None

        speak("अलार्म बंद कर दिया गया")

        if current_alarm in alarms:
            alarms.remove(current_alarm)

        current_alarm = None
    else:
        speak("कोई अलार्म बज नहीं रहा")

def alarm_loop():
    global alarm_playing, current_alarm
    while True:
        now = datetime.now()
        for a in alarms[:]:
            if now >= a:
                alarms.remove(a)
                play_alarm(a)
        time.sleep(1)
 
def snooze_alarm():
    global current_alarm, alarm_playing, alarm_process, alarms

    if not alarm_playing or current_alarm is None:
        speak("कोई अलार्म बज नहीं रहा")
        return

    # stop current alarm sound
    alarm_playing = False

    if alarm_process:
        try:
            alarm_process.kill()
        except Exception:
            pass
        alarm_process = None

    # schedule snooze after 5 minutes
    new_time = datetime.now() + timedelta(minutes=5)
    alarms.append(new_time)

    speak("अलार्म 5 मिनट के लिए स्थगित कर दिया गया")

    current_alarm = None       


def play_timer_sound():
	for _ in range(5):
		
		os.system('aplay timer.wav')
	speak("टाइमर खत्म हो गया")
    
def stop_song():
    global music_process

    if music_process and music_process.poll() is None:
        music_process.kill()
        music_process = None
        #speak("गाना बंद कर दिया")
        #return
    os.system("pkill -f ffplay")
    os.system("pkill -f mpg123")
    speak("गाना बंद कर दिया")
        
    #else:
    #   speak("कोई गाना नहीं चल रहा")

def led_on():
    led.on()
    speak("लाइट चालू कर दी")

def led_off():
    led.off()
    speak("लाइट ऑफ कर दी")

def clean_text(text):
    stop_words = ["क्या", "कौन", "है", "का", "की", "के", "में", "हैं", "था", "थे"]
    words = text.split()
    return [w for w in words if w not in stop_words]

stfile_path = "/home/srinidhi2/vosk_env/stories.json"
def load_diary():
	if not os.path.exists(DIARY_FILE):
		with open(DIARY_FILE, 'w', encoding="utf-8") as f:
			json.dump([], f, ensure_ascii=False)
	with open(DIARY_FILE,'r',encoding="utf-8") as f:
		return json.load(f)
	print(0)

def save_diary(data):
	with open(DIARY_FILE,'w',encoding="utf-8") as f:
         json.dump(data, f, ensure_ascii=False,indent=2)
def add_diary_entry(text):
	diary = load_diary()
	now = datetime.now()
	entry = {"date":now.strftime("%Y-%m-%d"), "time":now.strftime("%H:%M"), "text":text}
	diary.append(entry)
	save_diary(diary)
	speak("आपकी डायरी अपडेट हो गई")

def read_diary():
    diary = load_diary()
    if not diary:
        speak("आपकी डायरी खाली है")
        return
    speak(f"आपकी डायरी में {len(diary)} प्रविष्टियाँ हैं")
    for entry in diary:
        speak(f"दिनांक: {entry['date']}, समय: {entry['time']}")
        speak(entry["text"])



def load_stories(stfile_path):
    with open(stfile_path, "r", encoding="utf-8") as f:
        return json.load(f)
stories = load_stories(stfile_path)        
def tell_moral_story(stories, speak):
	global stop_story_flag
	stop_story_flag = False
	story = random.choice(stories)
	speak("शीर्षक। " + story["शीर्षक"])
	time.sleep(0.5)
	#speak("कहानी सुनिए।")
	time.sleep(0.5)
	for line in story["कहानी"]:
		if stop_story_flag:
			speak("ठीक है, कहानी रोक दी")
			return
			
		speak(line)
		time.sleep(0.4)
	speak("शिक्षा। " + story["शिक्षा"])
    
def stop_story():
    global stop_story_flag
    stop_story_flag = True


def translate_and_speak(word):
    word = word.strip().split()   

    if word[0] in hindi_dict:
        meaning = hindi_dict[word[0]]
        output = f"{word[0]} : {meaning}"
        print(output)
        speak(output)
    else:
        speak("शब्द नहीं मिला")
    
def play_song(song_text):
    global music_process, current_song_index

    for i, (key, file) in enumerate(SONGS.items()):
        if key in song_text:
            current_song_index = i
            path = os.path.join(MUSIC_FOLDER, file)

            if os.path.exists(path):
                speak(f"{key} चला रही हूँ")

                if music_process and music_process.poll() is None:
                    music_process.kill()

                music_process = subprocess.Popen(
                    ["ffplay", "-nodisp", "-autoexit", path],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                return

    speak("यह गाना नहीं मिला")

def answer_gk_question(text, hindi_gk):
    user_words = set(clean_text(text))

    best_match = None
    max_overlap = 0

    for q, ans in hindi_gk.items():
        q_words = set(clean_text(q))
        overlap = len(user_words & q_words)

        if overlap > max_overlap:
            max_overlap = overlap
            best_match = ans

    if max_overlap >= 2:   # threshold
        speak(best_match)
        return True

    speak("मुझे इसका सही जवाब नहीं पता।")
    return False
    
def add_timer(minutes):
    global stop_timer_flag
    stop_timer_flag = False
    trigger_time = datetime.now() + timedelta(minutes=minutes)
    timers.append(trigger_time)
    speak(f"{minutes} मिनट का टाइमर लगाया गया")

def timer_loop():
    global stop_timer_flag
    while True:
        if stop_timer_flag:
            if timers:
                timers.clear()
                speak("टाइमर रोक दिया गया")
        now = datetime.now()
        for t in list(timers):
            if now >= t:
                play_timer_sound()
                timers.remove(t)
        time.sleep(1)
        
def stop_timer():
    global stop_timer_flag, timers
    if timers:
        timers.clear()
        stop_timer_flag = True
        speak("टाइमर रोक दिया गया")
    else:
        speak("कोई टाइमर नहीं चल रहा")
        
    
def change_song():
    global current_song_index

    if not song_keys:
        speak("कोई गाना उपलब्ध नहीं है")
        return

    current_song_index = (current_song_index + 1) % len(song_keys)
    next_song = song_keys[current_song_index]

    play_song(next_song)
    

def get_timestamp():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

print(get_timestamp())

def get_temperature():
    try:
        temp = dhtDevice.temperature
        hum = dhtDevice.humidity

        speak(f"तापमान: {temp}°C")
        speak(f"आर्द्रता: {hum}%")
        
    except RuntimeError:
        speak("सेंसर पढ़ने में समस्या")
        return None, None
        
def get_bearing(lat1, lon1, lat2, lon2):
    dLon = math.radians(lon2 - lon1)
    y = math.sin(dLon) * math.cos(math.radians(lat2))
    x = math.cos(math.radians(lat1))*math.sin(math.radians(lat2)) - \
        math.sin(math.radians(lat1))*math.cos(math.radians(lat2))*math.cos(dLon)
    return math.degrees(math.atan2(y, x))
    
def get_node_from_street(G, street_name_hindi):
    # Convert Hindi to English using your JSON
    with open("street_translation.json", "r", encoding="utf-8") as f:
        street_dict = json.load(f)
    english_name = None

    for eng, hin in street_dict.items():
        if hin is None:
            continue
        if normalize(hin) in normalize(street_name_hindi):
            english_name = eng
            break

    if not english_name:
        return None

    # Search street inside graph
    for u, v, data in G.edges(data=True):
        if "name" in data:
            name = data["name"]
            if isinstance(name, list):
                name = name[0]

            if normalize(english_name) in normalize(name):
                return u

    return None
    
def start_navigation(start_place, end_place):
    global navigation_instructions, current_step_index, navigation_active

    speak("मार्ग खोजा जा रहा है")

    G = ox.graph_from_xml("maptest.osm")

    

    orig_node = get_node_from_street(G, start_place)
    dest_node = get_node_from_street(G, end_place)
    
    if orig_node is None or dest_node is None:
        speak("स्थान मानचित्र में नहीं मिला")
        return
    if orig_node == dest_node:
        speak("शुरुआत और गंतव्य बहुत पास हैं")
        return
    

    route = nx.shortest_path(G, orig_node, dest_node, weight="length")

    navigation_instructions = []
    prev_bearing = None

    for i in range(len(route) - 1):

        n1 = G.nodes[route[i]]
        n2 = G.nodes[route[i+1]]

        edge_data = G.get_edge_data(route[i], route[i+1])
        edge = list(edge_data.values())[0]
        length = edge.get("length", 0)
        road_name = edge.get("name", "")

        if isinstance(road_name, list):
            road_name = road_name[0]

        current_bearing = get_bearing(n1["y"], n1["x"], n2["y"], n2["x"])

        if prev_bearing is None:
            msg = f"{length:.0f} मीटर {road_name} पर आगे बढ़ें"

        else:
            turn = current_bearing - prev_bearing

            if turn > 180:
                turn -= 360
            elif turn < -180:
                turn += 360

            if turn > 35:
                msg = f"{length:.0f} मीटर बाद {road_name} पर दाएँ मुड़ें"
            elif turn < -35:
                msg = f"{length:.0f} मीटर बाद {road_name} पर बाएँ मुड़ें"
            else:
                msg = f"{length:.0f} मीटर {road_name} पर सीधे चलें"

        navigation_instructions.append(msg)
        prev_bearing = current_bearing

    navigation_instructions.append("आप गंतव्य पर पहुँच गए")

    current_step_index = 0
    navigation_active = True

    speak("मार्ग मिल गया")
    speak(navigation_instructions[current_step_index])

def handle_calculator_command(text):
    words = text.split()
    
    # Hindi number mapping
    hindi_numbers = {
        "शून्य": 0,
        "एक": 1,
        "दो": 2,
        "तीन": 3,
        "चार": 4,
        "पांच": 5,
        "छह": 6,
        "सात": 7,
        "आठ": 8,
        "नौ": 9,
        "दस": 10,
        "ग्यारह": 11,
        "बारह": 12,
        "तेरह": 13,
        "चौदह": 14,
        "पंद्रह": 15,
        "सोलह": 16,
        "सत्रह": 17,
        "अठारह": 18,
        "उन्नीस": 19,
        "बीस": 20
    }

    num1 = None
    num2 = None
    operator = None

    for w in words:
        # Number detection
        if w.isdigit():
            num = int(w)
        elif w in hindi_numbers:
            num = hindi_numbers[w]
        else:
            num = None

        if num is not None:
            if num1 is None:
                num1 = num
            else:
                num2 = num

        # Operator detection
        if w in operator_map:
            operator = operator_map[w]

    if num1 is not None and num2 is not None and operator:
        try:
            result = eval(f"{num1}{operator}{num2}")
            speak(f"उत्तर है {result}")
        except Exception:
            speak("गणना में समस्या आई")
    else:
        speak("कृपया सही गणना बोलिए")
        
def tell_joke():
    speak(random.choice(JOKES))
def tell_riddles():
    speak(random.choice(RIDDLES))
def tell_positive():
    speak(random.choice(POSITIVE_LINES))
def tell_tonguetwisters():
    speak(random.choice(TONGUE_TWISTERS))
# ===== VOSK =====
model = Model("vosk-model-small-hi-0.22")
#model_en = Model("vosk-model-small-en-us-0.15")
rec = KaldiRecognizer(model, 16000)
#rec_en = KaldiRecognizer(model_en, 16000)

activated = False
waiting_for_song = False

def in_active_window():
    return time.time() < active_until
    
def handle_alarm_time(text):
    global alarm_setting

    alarm_time = parse_hindi_time(text)

    if alarm_time:
        alarms.append(alarm_time)   # schedule, don't ring now
        speak(f"अलार्म {alarm_time.hour} बजे {alarm_time.minute} मिनट पर लगा दिया गया")
        alarm_setting = False
    else:
        speak("समय समझ नहीं आया, फिर से बोलिए")

def callback(indata, frames, time_info, status):
    global activated, waiting_for_song, wait_min, wait_for_snooze,alarm_setting,waiting_for_diary, stop_story_flag, stop_timer_flag
    
    #alarm_setting = False
 
    if rec.AcceptWaveform(indata.tobytes()):
        result = json.loads(rec.Result())
        text = result.get("text", "").lower()

        if not text:
            return

        print("सुना:", text)
        if alarm_playing and ("खत्म" in text):
            stop_alarm()
            return 
        if "स्थगित" in text:
            snooze_alarm()
            return
        if "डायरी सुनाओ" in text:
            speak("डायरी पढ़ रहा हूँ")
            read_diary()
            return
        if alarm_setting:
            handle_alarm_time(text)
            return
        if waiting_for_diary:
            add_diary_entry(text)
            waiting_for_diary=False
            return
        if stop_timer_flag is False:
            if ("रुको" in text):
                stop_timer()
                return 
        if wait_min:
            handle_timer_command(text)
            return
         
            
        if "बंद" in text:   ##May not be ideal!
            stop_song()
            waiting_for_song = False
            return
        if "बस करो" in text:
            stop_story()
            return

        if waiting_for_song:
            play_song(text)
            waiting_for_song = False
            activated = False
            return
        '''if not activated:
            if WAKE_WORD in text:
                activated = True
                speak("हाँ, बोलिए")
        else:
            intent = recognize_intent(text)'''

        #Replacing to include sleepword
        global active_until

        # ---- SLEEP WORD CHECK (highest priority) ----
        for w in SLEEP_WORDS:
            if w in text:
                activated = False
                active_until = 0
                speak("ठीक है, मैं चुप हो रही हूँ")
                return


        # ---- WAKE WORD ----
        if WAKE_WORD in text:
            activated = True
            active_until = time.time() + ACTIVE_WINDOW
            speak("हाँ, बोलिए")
            return


        # ---- IF ALREADY IN 15s WINDOW ----
        if activated or in_active_window():

            # extend window on every valid command
            active_until = time.time() + ACTIVE_WINDOW

            intent = recognize_intent(text)

            # ---- NAVIGATION INTENT ----
            if intent == "navigate":
                if "जाना" in text and "से" in text:
                    parts = text.split(" से ")
                    print(parts)
                    if "मुझे" in parts:
                        parts.remove("मुझे")
                    start_place = parts[0].replace("जाना है", "").strip()
                    end_place = parts[1].replace("जाना", "").replace("है","").strip()    
                        
                    speak(f"शुरुआत: {start_place}")
                    speak(f"गंतव्य: {end_place}")

                    start_navigation(start_place, end_place)
                else:
                    speak("कृपया 'से' और 'जाना है' के साथ पूरा वाक्य बोलिए")
            elif intent == "next_step":
                if navigation_active and current_step_index + 1 < len(navigation_instructions):
                    current_step_index += 1
                    speak(navigation_instructions[current_step_index])
                else:
                    speak("कोई अगला चरण नहीं है")
            elif intent == "play_song":
                speak("कौन सा गाना?")
                waiting_for_song = True
                return
            
            elif intent == "stop_song":
                stop_song()
            
            elif intent == "joke":
                tell_joke()
            
            elif intent == "positive":
                tell_positive()
            
            elif intent == "tongue_twister":
                tell_tonguetwisters()
            
            elif intent == "temperature":
                get_temperature()
            
            elif intent == "riddle":
                tell_riddles()

            elif intent == "change_song":
                change_song()
          
            elif intent == "led_on":
                led_on()
            
            elif intent == "dictionary":
                translate_and_speak(text)
                return

            elif intent == "alarm_snooze":
                snooze_alarm()    
                   
            elif intent == "led_off":
                led_off()
            elif intent == "alarm_stop":
                stop_alarm()
            elif intent == "alarm":
                speak("कृपया समय बताइए, जैसे सात बजे तीस मिनट")
                alarm_setting = True
                return
  	
            elif intent == "samay":
                speak(datetime.now().strftime("समय %H:%M है"))

            elif intent == "timer":
                handle_timer_command(text)
            elif intent == "stop_timer":
                stop_timer()
                #return
            elif intent=="voice_diary":
                speak("कृपया बोलिए, मैं आपकी डायरी में सेव कर दूँगी")
                waiting_for_diary=True
                return
            elif intent == "read_diary":
                read_diary()
                return            
            elif intent == "tell_story":
                speak("ठीक है")
                threading.Thread(
                    target=tell_moral_story,
                    args=(stories, speak),
                    daemon=True
                ).start()
                
            elif intent == "stop_story":
                stop_story_flag = True
                speak("ठीक है।")
                return
				
            elif intent == "calculator":
                handle_calculator_command(text)
                
             
            elif intent == "gk_question":
                 if answer_gk_question(text,hindi_gk):
                    return
               
            elif intent == "date":
                today = datetime.now()
                days_hi = {
                "Monday": "सोमवार",
                "Tuesday": "मंगलवार",
                "Wednesday": "बुधवार",
                "Thursday": "गुरुवार",
                "Friday": "शुक्रवार",
                "Saturday": "शनिवार",
                "Sunday": "रविवार"
                    }
                    
                months_hi = {
                "January": "जनवरी",
                "February": "फ़रवरी",
                "March": "मार्च",
                "April": "अप्रैल",
                "May": "मई",
                "June": "जून",
                "July": "जुलाई",
                "August": "अगस्त",
                "September": "सितंबर",
                "October": "अक्टूबर",
                "November": "नवंबर",
                "December": "दिसंबर"
                    }
                    
                day = days_hi[today.strftime("%A")]
                month = months_hi[today.strftime("%B")]
                date_num = today.strftime("%d")
                year = today.strftime("%Y")
            
                speak(f"आज {day}, {date_num} {month} {year} है")


            else:
                speak("मुझे समझ नहीं आया")

            #activated = False

def handle_timer_command(text):
    global wait_min
    words = text.split()

    for w in words:
        if w.isdigit():
            add_timer(int(w))
            wait_min = False
            return

    for w in words:
        if w in hindi_number_map:
            add_timer(hindi_number_map[w])
            wait_min = False
            return

    speak("कितने मिनट का टाइमर लगाऊँ?")
    wait_min = True

threading.Thread(
    target=alarm_loop,
    daemon=True
).start()

threading.Thread(
    target=timer_loop,
    daemon=True
).start()

with sd.InputStream(
    samplerate=16000,
    channels=1,
    dtype='int16',
    latency="low",
    callback=callback
):
    print("Voice assistant ready")
    while True:
        time.sleep(0.02)
