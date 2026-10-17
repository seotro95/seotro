"""Language labels and actual engine capabilities; country labels are not accent promises."""
CORE_LANGUAGES={'vi':'Việt Nam · Tiếng Việt','en-US':'Mỹ · English','en-GB':'Anh · English','ja':'Nhật Bản · 日本語','ko':'Hàn Quốc · 한국어','zh':'Trung Quốc · 中文','fr':'Pháp · Français','de':'Đức · Deutsch','es':'Tây Ban Nha · Español','it':'Ý · Italiano','pt':'Bồ Đào Nha / Brazil · Português','ru':'Nga · Русский'}
EXTRA_LANGUAGES={'th':'Thái Lan · ไทย','id':'Indonesia · Bahasa Indonesia','ms':'Malaysia · Bahasa Melayu','tl':'Philippines · Tagalog','km':'Campuchia · ខ្មែរ','lo':'Lào · ລາວ','my':'Myanmar · မြန်မာ','hi':'Ấn Độ · हिन्दी','bn':'Bangladesh · বাংলা','ta':'Ấn Độ / Sri Lanka · தமிழ்','te':'Ấn Độ · తెలుగు','ur':'Pakistan · اردو','ar':'Ả Rập · العربية','fa':'Iran · فارسی','he':'Israel · עברית','tr':'Thổ Nhĩ Kỳ · Türkçe','nl':'Hà Lan · Nederlands','sv':'Thụy Điển · Svenska','da':'Đan Mạch · Dansk','no':'Na Uy · Norsk','fi':'Phần Lan · Suomi','pl':'Ba Lan · Polski','cs':'Séc · Čeština','sk':'Slovakia · Slovenčina','hu':'Hungary · Magyar','ro':'Romania · Română','bg':'Bulgaria · Български','el':'Hy Lạp · Ελληνικά','uk':'Ukraine · Українська','hr':'Croatia · Hrvatski','sr':'Serbia · Српски','sl':'Slovenia · Slovenščina','lt':'Lithuania · Lietuvių','lv':'Latvia · Latviešu','et':'Estonia · Eesti','sw':'Đông Phi · Kiswahili','af':'Nam Phi · Afrikaans','ne':'Nepal · नेपाली','si':'Sri Lanka · සිංහල','mn':'Mông Cổ · Монгол'}
LANGUAGES={**CORE_LANGUAGES,**EXTRA_LANGUAGES}
QWEN_LANGUAGES=tuple(k for k in CORE_LANGUAGES if k!='vi')
SUBTITLE_LANGUAGES=LANGUAGES
RECOGNITION_CODES={key.split('-')[0] for key in LANGUAGES}

def system_language(culture):
    if culture in ('en-US','en-GB'):return culture
    base=culture.split('-')[0].lower()
    return 'en-US' if base=='en' else base

def native_language(voice):
    ident=voice['id']
    if voice.get('engine')=='system':return voice.get('culture',voice['languages'][0]).split('-')[0]
    if voice.get('category')=='cloned':return voice['languages'][0].split('-')[0]
    if ident.startswith(('vi-','nano-')):return 'vi'
    if ident in ('qw-ryan','qw-aiden'):return 'en'
    if ident=='qw-ono':return 'ja'
    if ident=='qw-sohee':return 'ko'
    return 'zh'
