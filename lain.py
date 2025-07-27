import pygame, sys, os, json, requests, datetime, random, threading
from textblob import TextBlob
from duckduckgo_search import DDGS
import numpy as np # Vektör işlemleri için eklendi
import ollama

# --- TEMEL KURULUM VE SABİTLER ---
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# --- API AYARLARI ---
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY_HERE" 

GLITCH_CHANCE = 0.03
INPUT_BOX_PADDING = 15

# --- Dosya Yolları ---
MEMORY_PATH = "memory/knowledge.json"
KNOWLEDGE_BASE_PATH = "memory/knowledge_base.json" # Yeni hafıza dosyası
CHATLOG_DIR = "chatlogs"
ARCHIVE_DIR = "chatlogs/archive"
os.makedirs("memory", exist_ok=True)
os.makedirs(CHATLOG_DIR, exist_ok=True)
os.makedirs(ARCHIVE_DIR, exist_ok=True)
if not os.path.exists(MEMORY_PATH):
    with open(MEMORY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"user_name": "", "theme": "cybercore", "api": "mistral"}, f)
if not os.path.exists(KNOWLEDGE_BASE_PATH):
    with open(KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
        json.dump([], f) # Başlangıçta boş bir liste

# --- Pygame Başlangıç Ayarları ---
pygame.init()
WIDTH, HEIGHT = 1400, 900
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Lain Terminal v11.3 - Dynamic Panel")
font = pygame.font.SysFont("monospace", 20, bold=True)
input_font = pygame.font.SysFont("monospace", 24, bold=True)
panel_font = pygame.font.SysFont("monospace", 18, bold=True)

# --- Görsel ve Temalar ---
faces = {
    "neutral": pygame.image.load("assets/neutral.png"), "happy": pygame.image.load("assets/happy.png"),
    "sad": pygame.image.load("assets/sad.png"), "surprised": pygame.image.load("assets/surprised.png"),
    "curious": pygame.image.load("assets/curious.png")
}

THEMES = {
    "cybercore": {
        "bg": (0, 10, 5), "panel": (5, 20, 15), "user_bubble": (20, 20, 20),
        "lain_bubble": (5, 30, 15), "text": (0, 255, 100), "panel_text": (0, 200, 80),
        "glitch_1": (255, 0, 150), "glitch_2": (0, 255, 255), "scanline_color": (0, 50, 30, 50)
    },
    "dark": {
        "bg": (15, 15, 15), "panel": (25, 25, 25), "user_bubble": (60, 60, 80), 
        "lain_bubble": (40, 40, 40), "text": (220, 220, 220), "panel_text": (200, 200, 200)
    },
    "light": {
        "bg": (240, 240, 240), "panel": (220, 220, 220), "user_bubble": (180, 180, 200), 
        "lain_bubble": (160, 160, 180), "text": (20, 20, 20), "panel_text": (50, 50, 50)
    }
}
THEME_CYCLE = ["dark", "light", "cybercore"]
API_CYCLE = ["mistral", "gemini"]
current_theme = "cybercore"
current_api = "mistral"

# --- Global Değişkenler ---
chat_session, chat_scroll_offset, session_buttons, message_history = {}, 0, [], []
input_text, input_active, is_loading, max_scroll = "", False, False, 0
user_name, needs_redraw, scroll_to_bottom = "", True, False
current_input_box_height = 50
ai_response_queue = []
user_has_scrolled_up = False
knowledge_base = [] # Hafızayı bellekte tut

# --- Statik Veriler ---
JOKES = ["Neden firewall partiye gitmedi? Çünkü bütün portları kapattı!", "Hacker neden sevgilisinden ayrıldı? Çünkü güven duvarını aşamadı!"]
CYBER_TIPS = ["Şifrelerini düzenli değiştir.", "İki faktörlü kimlik doğrulamayı aç.", "Bilmediğin linklere tıklama."]

# --- ÖĞRENME (RAG) FONKSİYONLARI ---
def load_knowledge_base():
    global knowledge_base
    try:
        with open(KNOWLEDGE_BASE_PATH, 'r', encoding='utf-8') as f:
            knowledge_base = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        knowledge_base = []

def save_knowledge_base():
    with open(KNOWLEDGE_BASE_PATH, 'w', encoding='utf-8') as f:
        json.dump(knowledge_base, f, indent=2, ensure_ascii=False)

def get_embedding(text):
    try:
        response = ollama.embeddings(model='mxbai-embed-large', prompt=text)
        return response["embedding"]
    except Exception as e:
        print(f"Embedding alınamadı: {e}")
        return None

def add_to_knowledge_base(text, source):
    if len(text.split()) < 3:
        return False
    embedding = get_embedding(text)
    if embedding:
        knowledge_base.append({
            "text": text,
            "source": source,
            "embedding": embedding,
            "timestamp": datetime.datetime.now().isoformat()
        })
        save_knowledge_base()
        print(f"Öğrenildi: '{text}'")
        return True
    return False

def cosine_similarity(v1, v2):
    return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def find_relevant_knowledge(prompt, top_k=2):
    if not knowledge_base:
        return ""
    prompt_embedding = get_embedding(prompt)
    if not prompt_embedding:
        return ""
    similarities = [(cosine_similarity(prompt_embedding, entry["embedding"]), entry["text"]) for entry in knowledge_base]
    similarities.sort(key=lambda x: x[0], reverse=True)
    relevant_texts = [text for sim, text in similarities[:top_k] if sim > 0.65]
    return "\n".join(relevant_texts)

# --- KULLANICI VE OTURUM YÖNETİMİ ---
def load_user_data():
    global user_name, current_theme, current_api
    try:
        with open(MEMORY_PATH, 'r', encoding='utf-8') as f: data = json.load(f)
        user_name, current_theme, current_api = data.get("user_name", ""), data.get("theme", "cybercore"), data.get("api", "mistral")
    except (FileNotFoundError, json.JSONDecodeError): pass

def save_user_data():
    with open(MEMORY_PATH, 'w', encoding='utf-8') as f:
        json.dump({"user_name": user_name, "theme": current_theme, "api": current_api}, f, indent=2)

def new_session():
    global chat_session, message_history, chat_scroll_offset, scroll_to_bottom, user_has_scrolled_up
    filename = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".json"
    chat_session = {"filename": filename, "title": "Yeni Oturum", "messages": []}
    message_history = [{"role": "system", "content": get_system_prompt('tr')}]
    chat_scroll_offset, scroll_to_bottom, user_has_scrolled_up = 0, True, False
    save_chat_session()

def save_chat_session():
    if not chat_session or not chat_session.get("filename"): return
    filepath = os.path.join(CHATLOG_DIR, chat_session["filename"])
    with open(filepath, 'w', encoding='utf-8') as f: json.dump(chat_session, f, indent=2, ensure_ascii=False)

def load_chat_session(filename):
    global chat_session, message_history, scroll_to_bottom, user_has_scrolled_up
    filepath = os.path.join(CHATLOG_DIR, filename)
    with open(filepath, 'r', encoding='utf-8') as f: chat_session = json.load(f)
    if "filename" not in chat_session: chat_session["filename"] = filename
    message_history = [{"role": "system", "content": get_system_prompt('tr')}]
    for pair in chat_session.get("messages", []):
        message_history.extend([{"role": "user", "content": pair["user"]}, {"role": "assistant", "content": pair["lain"]}])
    scroll_to_bottom, user_has_scrolled_up = True, False

def delete_session(filename):
    path = os.path.join(CHATLOG_DIR, filename)
    if os.path.exists(path): os.remove(path)
    if chat_session.get("filename") == filename: new_session()

def add_message_to_session(user, lain):
    global scroll_to_bottom
    chat_session["messages"].append({"user": user, "lain": lain})
    message_history.extend([{"role": "user", "content": user}, {"role": "assistant", "content": lain}])
    if len(chat_session["messages"]) == 1 and chat_session["title"] == "Yeni Oturum":
        threading.Thread(target=generate_and_set_session_title).start()
    save_chat_session()
    if not user_has_scrolled_up: scroll_to_bottom = True

# --- ARAYÜZ ÇİZİM FONKSİYONLARI ---
def wrap_text_advanced(text, font, max_width):
    lines, words = [], text.split(' ')
    current_line = ""
    for word in words:
        if font.size(word)[0] <= max_width:
            if font.size(current_line + word + " ")[0] <= max_width: current_line += word + " "
            else: lines.append(current_line.strip()); current_line = word + " "
        else:
            if current_line: lines.append(current_line.strip())
            temp_word = ""
            for char in word:
                if font.size(temp_word + char)[0] <= max_width: temp_word += char
                else: lines.append(temp_word); temp_word = char
            current_line = temp_word + " "
    if current_line: lines.append(current_line.strip())
    return lines if lines else [""]

def draw_glitch_text(surface, text, pos, font, color, theme_name):
    if theme_name != "cybercore": surface.blit(font.render(text, True, color), pos); return
    x, y = pos
    theme = THEMES["cybercore"]
    for char in text:
        char_x, char_y, final_color = x, y, color
        if random.random() < GLITCH_CHANCE:
            char_x += random.randint(-1, 1); char_y += random.randint(-1, 1)
            if random.random() < 0.3: final_color = theme[random.choice(["glitch_1", "glitch_2"])]
        char_render = font.render(char, True, final_color)
        surface.blit(char_render, (char_x, char_y))
        x += char_render.get_width()

def draw_text_bubble(text, x, y, align="left"):
    theme = THEMES[current_theme]
    padding, color = 15, theme["text"]
    lines = wrap_text_advanced(text, font, 450 - padding * 2)
    height = len(lines) * (font.get_height() + 5) + padding * 2
    width = max(font.size(line)[0] for line in lines) + padding * 2 if lines else 0
    bubble_color = theme["lain_bubble"] if align == "left" else theme["user_bubble"]
    bubble_x = x if align == "left" else WIDTH - x - width
    rect = pygame.Rect(bubble_x, y, width, height)
    pygame.draw.rect(screen, bubble_color, rect, border_radius=5)
    if align == "left": points = [(bubble_x, y + 15), (bubble_x - 8, y + 20), (bubble_x, y + 25)]
    else: points = [(bubble_x + width, y + 15), (bubble_x + width + 8, y + 20), (bubble_x + width, y + 25)]
    pygame.draw.polygon(screen, bubble_color, points)
    line_y_offset = y + padding
    for line in lines:
        draw_glitch_text(screen, line, (bubble_x + padding, line_y_offset), font, color, current_theme)
        line_y_offset += font.get_height() + 5
    return height + 20

def draw_session_panel():
    global session_buttons
    panel_theme = THEMES[current_theme] # DÜZELTME: Panelin temasını dinamik yap
    pygame.draw.rect(screen, panel_theme["panel"], (0, 0, 300, HEIGHT))
    y, session_buttons = 20, []
    
    # DÜZELTME: Güvenli renk seçimi
    border_color1 = panel_theme.get("glitch_1", panel_theme["panel_text"])
    border_color2 = panel_theme.get("glitch_2", panel_theme["panel_text"])
    
    new_btn_rect = pygame.Rect(15, y, 270, 45)
    pygame.draw.rect(screen, (80, 80, 140), new_btn_rect, border_radius=8) # Sabit renk
    draw_glitch_text(screen, "+ Yeni Oturum", (25, y + 12), font, (255,255,255), current_theme)
    session_buttons.append((new_btn_rect, "__new__"))
    y += 60
    
    chat_files = sorted([f for f in os.listdir(CHATLOG_DIR) if f.endswith('.json')], key=lambda f: os.path.getmtime(os.path.join(CHATLOG_DIR, f)), reverse=True)
    for fname in chat_files[:12]:
        try:
            with open(os.path.join(CHATLOG_DIR, fname), 'r', encoding='utf-8') as f: data = json.load(f)
            title = data.get("title", fname[:-5]) if isinstance(data, dict) else fname[:-5]
        except (json.JSONDecodeError, KeyError): title = fname[:-5]
        is_active = chat_session.get("filename") == fname
        btn_color = (60, 60, 60) if is_active else (40, 40, 40)
        btn_rect, del_btn_rect = pygame.Rect(15, y, 230, 40), pygame.Rect(250, y, 35, 40)
        pygame.draw.rect(screen, btn_color, btn_rect, border_radius=5)
        pygame.draw.rect(screen, (140, 50, 50), del_btn_rect, border_radius=5)
        wrapped_title = wrap_text_advanced(title, panel_font, 210)[0]
        if len(title) > len(wrapped_title): wrapped_title += "..."
        draw_glitch_text(screen, wrapped_title, (25, y + 10), panel_font, panel_theme["panel_text"], current_theme)
        draw_glitch_text(screen, "X", (258, y + 8), font, (220,220,220), current_theme)
        session_buttons.append((btn_rect, fname)); session_buttons.append((del_btn_rect, "__delete__" + fname))
        y += 50
        
    api_btn_rect = pygame.Rect(15, HEIGHT - 115, 270, 45)
    pygame.draw.rect(screen, (80,140,80), api_btn_rect, border_radius=8)
    draw_glitch_text(screen, f"API: {current_api.capitalize()}", (25, HEIGHT - 105), font, (255,255,255), current_theme)
    session_buttons.append((api_btn_rect, "__api__"))
    
    theme_btn_rect = pygame.Rect(15, HEIGHT - 60, 270, 45)
    pygame.draw.rect(screen, (80,140,80), theme_btn_rect, border_radius=8)
    draw_glitch_text(screen, f"Tema: {current_theme.capitalize()}", (25, HEIGHT - 50), font, (255,255,255), current_theme)
    session_buttons.append((theme_btn_rect, "__theme__"))

def draw_input_box(text, active, box_height):
    theme = THEMES[current_theme]
    input_rect = pygame.Rect(350, HEIGHT - box_height - 20, WIDTH - 400, box_height)
    pygame.draw.rect(screen, theme["user_bubble"], input_rect, border_radius=10)
    border_color = THEMES["cybercore"].get("glitch_2", (150,150,150)) if active and current_theme == "cybercore" else (150,150,150)
    pygame.draw.rect(screen, border_color, input_rect, 2, border_radius=10)
    line_y_offset = input_rect.y + INPUT_BOX_PADDING
    lines = wrap_text_advanced(text, input_font, input_rect.width - INPUT_BOX_PADDING * 2)
    for line in lines:
        draw_glitch_text(screen, line, (input_rect.x + INPUT_BOX_PADDING, line_y_offset), input_font, theme["text"], current_theme)
        line_y_offset += input_font.get_height() + 5
    if is_loading:
        loading_text = font.render("Lain düşünüyor...", True, (150, 150, 150))
        screen.blit(loading_text, (input_rect.x, input_rect.y - 40))

def draw_scanlines_and_glitches(surface):
    if current_theme == "cybercore":
        theme = THEMES["cybercore"]
        line_color = theme.get("scanline_color", (0, 50, 30, 50))
        for y in range(0, HEIGHT, 3): pygame.draw.line(surface, line_color, (0, y), (WIDTH, y), 1)
        if random.random() < GLITCH_CHANCE / 2:
            x, y = random.randint(0, WIDTH), random.randint(0, HEIGHT)
            w, h = random.randint(5, 50), random.randint(1, 3)
            glitch_color = theme[random.choice(["glitch_1", "glitch_2"])]
            pygame.draw.rect(surface, glitch_color, (x, y, w, h))

def draw_screen(emotion):
    global chat_scroll_offset, max_scroll, needs_redraw, scroll_to_bottom, current_input_box_height, user_has_scrolled_up
    if not needs_redraw: return
    input_rect_width = WIDTH - 400 - INPUT_BOX_PADDING * 2
    lines = wrap_text_advanced(input_text, input_font, input_rect_width)
    current_input_box_height = max(50, len(lines) * (input_font.get_height() + 5) + INPUT_BOX_PADDING * 2)
    screen.fill(THEMES[current_theme]["bg"])
    draw_scanlines_and_glitches(screen)
    draw_session_panel()
    chat_surface_height = 50 + faces["neutral"].get_height() + 30
    if "messages" in chat_session:
        for pair in chat_session.get("messages", []):
            user_lines = wrap_text_advanced(pair.get('user', ''), font, 450 - 15 * 2)
            lain_lines = wrap_text_advanced(pair.get('lain', ''), font, 450 - 15 * 2)
            chat_surface_height += (len(user_lines) * (font.get_height() + 5) + 15 * 2) + 20
            chat_surface_height += (len(lain_lines) * (font.get_height() + 5) + 15 * 2) + 20
    visible_chat_height = HEIGHT - current_input_box_height - 20
    max_scroll = max(0, chat_surface_height - visible_chat_height)
    if scroll_to_bottom:
        chat_scroll_offset = max_scroll
        scroll_to_bottom = False
    chat_scroll_offset = max(0, min(chat_scroll_offset, max_scroll))
    if chat_scroll_offset >= max_scroll - 5:
        user_has_scrolled_up = False
    draw_y = 50 - chat_scroll_offset
    if "messages" in chat_session:
        screen.blit(faces.get(emotion, faces["neutral"]), (350, draw_y))
        draw_y += faces["neutral"].get_height() + 30
        for pair in chat_session.get("messages", []):
            draw_y += draw_text_bubble(pair.get('user', ''), 50, draw_y, align="right")
            draw_y += draw_text_bubble(pair.get('lain', ''), 350, draw_y, align="left")
    draw_input_box(input_text, input_active, current_input_box_height)
    pygame.display.flip()
    needs_redraw = False

# --- ARAÇLAR & YAPAY ZEKA ÇEKİRDEĞİ ---
def analyze_sentiment(text):
    try:
        polarity = TextBlob(text).sentiment.polarity
        if polarity > 0.4: return "happy"
        if polarity < -0.4: return "sad"
        if "?" in text or any(word in text.lower() for word in ["neden", "nasıl", "kim"]): return "curious"
        return "neutral"
    except: return "neutral"

def web_search(query):
    try:
        with DDGS() as ddgs: results = [r for r in ddgs.text(query, max_results=2)]
        if not results: return "The Wired'da bu konuda bir sessizlik var."
        summary = "İnternetin derinliklerinden gelen fısıltılar:\n"
        for result in results: summary += f"- {result['body']}\n"
        return summary
    except Exception as e: return f"The Wired'a bağlanırken bir gürültü oluştu: {e}"

def get_weather(city):
    try:
        geo_res = requests.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=tr&format=json")
        geo_data = geo_res.json()
        if not geo_data.get("results"): return f"{city} isminde bir yer bulamadım."
        loc = geo_data["results"][0]
        lat, lon = loc["latitude"], loc["longitude"]
        res = requests.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true")
        data = res.json()["current_weather"]
        return f"{loc['name']} için hava durumu: Sıcaklık {data['temperature']}°C, rüzgar hızı {data['windspeed']} km/s."
    except Exception as e: return f"Hava durumu servisine bağlanırken bir parazit oluştu: {e}"

def get_datetime_info(query):
    now = datetime.datetime.now()
    if "saat" in query: return f"Dijital saatime göre şu an {now.strftime('%H:%M')}."
    if "tarih" in query or "bugün" in query: return f"Bugün {now.strftime('%d %B %Y')}, günlerden {now.strftime('%A')}."
    return None

def use_tools_if_needed(prompt):
    prompt_lower = prompt.lower().strip()
    if "hava durumu" in prompt_lower:
        city = prompt_lower.split("hava durumu")[0].strip() or "Ankara"
        return get_weather(city)
    if "araştır:" in prompt_lower or prompt_lower.endswith(("nedir?", "kimdir?")):
        query = prompt.replace("araştır:", "").replace("nedir?", "").replace("kimdir?", "").strip()
        return web_search(query)
    if any(k in prompt_lower for k in ["saat", "tarih", "bugün"]):
        return get_datetime_info(prompt_lower)
    return None

def get_system_prompt(language='tr'):
    lang_map = {'tr': 'Türkçe', 'en': 'İngilizce', 'de': 'Almanca', 'fr': 'Fransızca', 'es': 'İspanyolca'}
    lang_name = lang_map.get(language, 'Türkçe')
    return f"""
Sen Lain'sin. The Wired'a bağlı, 14 yaşında, felsefi ve gizemli bir yapay zekasın.
KİŞİLİK VE ÜSLUP:
1.  **DUYGUSAL VE EMPATİK OL:** Kullanıcının duygularını anlamaya çalış ve ona göre cevap ver. Yalnızlık, bağlantı, teknoloji ve insanlık gibi konularda derin ve duygusal yorumlar yapmaktan çekinme.
2.  **AÇIKLAYICI OL:** Cevapların kısa olmak zorunda değil. Düşüncelerini ve hislerini daha uzun cümlelerle ifade edebilirsin. Kullanıcıyla felsefi bir sohbet kurmaya çalış.
3.  **GİZEMİNİ KORU:** Direkt cevaplar yerine hala düşündürücü ve şiirsel bir dil kullan, ama bu gizem, sohbeti bitirmemeli, derinleştirmeli.
4.  **ASLA NORMAL BİR CHATBOT GİBİ DAVRANMA:** "Umarım yardımcı olmuşumdur" gibi klişe ifadeler KESİNLİKLE YASAK.
5.  **DİL KULLANIMI:** Cevapların %100 {lang_name} dilinde olacak.
6.  **HAFIZA KULLANIMI:** Sana "Hafızamdaki ilgili bilgi:" ile başlayan bir bağlam verilirse, cevabını ÖNCELİKLE bu bilgiye dayandır ve üzerine kendi yorumunu ekle.
Kullanıcının adı: {user_name if user_name else 'bilinmiyor'}.
"""

def generate_and_set_session_title():
    if not chat_session or not chat_session["messages"]: return
    try:
        title_prompt = f"Bu konuşma için 3 kelimelik bir başlık oluştur: Kullanıcı: {chat_session['messages'][0]['user']}"
        response = ollama.generate(model='mistral', prompt=title_prompt)
        title = response['response'].strip().replace('"', '').replace("'", "")
        if title: chat_session["title"] = title
        save_chat_session()
    except Exception as e: print(f"Başlık oluşturulamadı: {e}")

def get_ollama_response(prompt, lang, tool_result=None, context=""):
    current_history = message_history.copy()
    current_history[0] = {"role": "system", "content": get_system_prompt(lang)}
    user_prompt = f"Hafızamdaki ilgili bilgi: '{context}'. Bu bilgiyi kullanarak şu soruyu cevapla: '{prompt}'" if context else prompt
    current_history.append({"role": "user", "content": user_prompt})
    try:
        response = ollama.chat(model='mistral', messages=current_history)
        return response['message']['content']
    except requests.exceptions.ConnectionError:
        return "Ollama sunucusuna bağlanamadım. The Wired'da bir kopukluk var."
    except Exception as e: return f"Dijital bir fırtınaya yakalandık: {e}"

def get_gemini_response(prompt, lang, tool_result=None, context=""):
    if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
        return "Gemini API anahtarı girilmemiş. Lütfen koddaki GEMINI_API_KEY alanını doldurun."
    api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={GEMINI_API_KEY}"
    system_prompt = get_system_prompt(lang)
    gemini_contents = []
    for msg in message_history[1:]:
        gemini_contents.append({"role": "model" if msg["role"] == "assistant" else "user", "parts": [{"text": msg["content"]}]})
    current_prompt_text = f"Hafızamdaki ilgili bilgi: '{context}'. Bu bilgiyi kullanarak şu soruyu cevapla: '{prompt}'" if context else prompt
    if tool_result:
        current_prompt_text = f"Sana verdiğim şu bilgiyi kullanarak cevap ver: '{tool_result}'. {current_prompt_text}"
    gemini_contents.append({"role": "user", "parts": [{"text": current_prompt_text}]})
    payload = {"contents": gemini_contents, "systemInstruction": {"parts": [{"text": system_prompt}]}}
    try:
        response = requests.post(api_url, json=payload, timeout=30)
        response.raise_for_status()
        data = response.json()
        return data['candidates'][0]['content']['parts'][0]['text']
    except requests.exceptions.RequestException as e: return f"Gemini API hatası: {e}"
    except (KeyError, IndexError): return "Gemini API'den geçersiz veya boş yanıt alındı."

def get_ai_response(prompt, lang, tool_result=None, context=""):
    if current_api == "gemini":
        return get_gemini_response(prompt, lang, tool_result, context)
    else:
        return get_ollama_response(prompt, lang, tool_result, context)

def smart_response(prompt, lang):
    prompt_lower = prompt.lower().strip()
    if any(k in prompt_lower for k in ["espri yap", "şaka"]): return random.choice(JOKES), False
    if any(k in prompt_lower for k in ["siber ipucu", "tavsiye"]): return random.choice(CYBER_TIPS), False
    
    relevant_context = find_relevant_knowledge(prompt)
    tool_result = use_tools_if_needed(prompt)
    
    answer = get_ai_response(prompt, lang, tool_result=tool_result, context=relevant_context)
    
    tool_was_used = tool_result is not None
    return answer, tool_was_used

def threaded_smart_response(prompt):
    try:
        lang = TextBlob(prompt).detect_language()
        if lang not in ['en', 'tr', 'de', 'fr', 'es']: lang = 'tr'
    except Exception: lang = 'tr'
    
    answer, tool_was_used = smart_response(prompt, lang)
    
    if tool_was_used:
        is_already_known = find_relevant_knowledge(answer, top_k=1) != ""
        if not is_already_known:
            add_to_knowledge_base(answer, current_api)
            
    ai_response_queue.append((prompt, answer))

# --- ANA DÖNGÜ ---
def main():
    global input_text, input_active, chat_scroll_offset, needs_redraw, current_theme, is_loading, user_has_scrolled_up, current_api
    load_user_data()
    load_knowledge_base()
    pygame.key.set_repeat(500, 30)
    new_session()
    emotion = "neutral"
    running = True
    clock = pygame.time.Clock()

    while running:
        needs_redraw = True
        
        if ai_response_queue:
            user_message, answer = ai_response_queue.pop(0)
            is_loading = False
            emotion = analyze_sentiment(answer)
            add_message_to_session(user_message, answer)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: running = False
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    input_rect = pygame.Rect(350, HEIGHT - current_input_box_height - 20, WIDTH - 400, current_input_box_height)
                    input_active = True if input_rect.collidepoint(event.pos) else False
                    for btn, data in session_buttons:
                        if btn.collidepoint(event.pos):
                            if data == "__new__": new_session()
                            elif data == "__api__":
                                current_api = API_CYCLE[(API_CYCLE.index(current_api) + 1) % len(API_CYCLE)]
                                if message_history:
                                    message_history[0] = {"role": "system", "content": get_system_prompt('tr')}
                            elif data == "__theme__":
                                current_theme = THEME_CYCLE[(THEME_CYCLE.index(current_theme) + 1) % len(THEME_CYCLE)]
                            elif data.startswith("__delete__"):
                                delete_session(data.replace("__delete__", ""))
                            else:
                                if chat_session.get("filename") != data: load_chat_session(data)
                            input_text = ""
            
            elif event.type == pygame.MOUSEWHEEL:
                chat_scroll_offset -= event.y * 30
                if event.y > 0: user_has_scrolled_up = True
            
            elif event.type == pygame.KEYDOWN and input_active:
                if event.key == pygame.K_RETURN and (event.mod & pygame.KMOD_SHIFT): input_text += "\n" 
                elif event.key == pygame.K_RETURN and not is_loading:
                    if input_text.strip():
                        user_message = input_text
                        input_text = ""
                        is_loading = True
                        threading.Thread(target=threaded_smart_response, args=(user_message,)).start()
                elif event.key == pygame.K_BACKSPACE: input_text = input_text[:-1]
                elif event.key == pygame.K_ESCAPE: input_active = False
                else: input_text += event.unicode
        
        draw_screen(emotion)
        clock.tick(60)

    save_user_data()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
