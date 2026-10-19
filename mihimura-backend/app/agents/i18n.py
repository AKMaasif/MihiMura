"""Fixed farmer-facing text used by the deterministic (non-model) agent paths.

Every entry has English, Sinhala and Tamil versions. Use :func:`t` to fetch a
string in the turn's language; placeholders use ``str.format`` names.
These texts were reviewed for each language — edit all three together.
"""

from __future__ import annotations

from typing import Any

from app.services.language import normalize_language

EN, SI, TA = "English", "Sinhala", "Tamil"

TEXT: dict[str, dict[str, Any]] = {
    # ------------------------------------------------------------------ mode guard
    "mode_switch": {
        EN: {
            "summary": "This request fits {suggested} better than {current}.",
            "action": "Switch to {suggested} so MihiMura can use the right workflow and tools.",
            "follow": "Choose Switch & continue, or stay in the current mode if you only want a general answer.",
            "alternative": "Stay in {current} with reduced capabilities",
            "reason": None,  # English uses the router's own reason
            "do_not": ["Do not present a simple-chat answer as live or field-verified evidence when the request needs tool-grounded decision support."],
            "counter": "If your intent is only a general explanation rather than a real farm decision, staying in Simple Chat may be appropriate.",
        },
        SI: {
            "summary": "මෙම ඉල්ලීම {current} ට වඩා {suggested} ක්‍රමයට වඩා හොඳින් ගැළපේ.",
            "action": "නිවැරදි මෙවලම් සහ දත්ත භාවිතා කිරීමට {suggested} වෙත මාරු වන්න.",
            "follow": "‘Switch & continue’ තෝරන්න, නැතහොත් සාමාන්‍ය පිළිතුරක් පමණක් අවශ්‍ය නම් වත්මන් ක්‍රමයේ සිටින්න.",
            "alternative": "අඩු හැකියාවන් සමඟ {current} තුළම සිටින්න",
            "reason": "ඔබගේ ප්‍රශ්නයේ අර්ථය අනුව සජීවී දත්ත/ක්ෂේත්‍ර තීරණ හෝ සම්පූර්ණ වාර්තා workflow එකක් වඩා සුදුසු බව intent router හඳුනාගෙන ඇත.",
            "do_not": ["සජීවී දත්ත අවශ්‍ය ප්‍රශ්නයකට Simple Chat පිළිතුරක් field-verified evidence ලෙස භාවිතා නොකරන්න."],
            "counter": "ඔබට අවශ්‍ය වන්නේ සාමාන්‍ය පැහැදිලි කිරීමක් පමණක් නම් වත්මන් mode එකේ සිටීම සුදුසු විය හැක.",
        },
        TA: {
            "summary": "இந்த கோரிக்கை {current}-ஐ விட {suggested} முறைக்கு சிறப்பாக பொருந்துகிறது.",
            "action": "சரியான கருவிகள் மற்றும் தரவை பயன்படுத்த {suggested} முறைக்கு மாறவும்.",
            "follow": "‘Switch & continue’ என்பதை தேர்வு செய்யவும்; பொதுவான பதில் மட்டும் வேண்டுமெனில் தற்போதைய முறையில் தொடரலாம்.",
            "alternative": "குறைந்த திறன்களுடன் {current} முறையில் தொடரவும்",
            "reason": "உங்கள் கேள்வியின் நோக்கத்தைப் பார்த்து நேரடி தரவு/வயல் முடிவு அல்லது முழு அறிக்கை workflow சிறந்தது என்று intent router கண்டறிந்துள்ளது.",
            "do_not": ["நேரடி தரவு தேவைப்படும் கேள்விக்கு Simple Chat பதிலை field-verified evidence என பயன்படுத்த வேண்டாம்."],
            "counter": "உங்களுக்கு பொதுவான விளக்கம் மட்டும் தேவைப்பட்டால் தற்போதைய mode-ல் தொடர்வது சரியாக இருக்கலாம்.",
        },
    },
    # ------------------------------------------------------------- report: clarify
    "clarify": {
        EN: {
            "labels": {"crop": "crop", "location": "location", "area_value": "land area"},
            "known_default": "your report goal",
            "summary": "I have {known}. I only need the report-blocking details below; I can handle season, irrigation, variety and planting date as visible assumptions if you do not know them yet.",
            "action": "Complete only the required fields below, then MihiMura will continue without additional mandatory popups.",
            "why": "Crop, location and land area determine the scope of the agronomic, resource and financial calculations. Other unknowns can be shown as assumptions and refined later.",
            "alternatives": ["Provide the missing detail in normal chat instead of using the form", "Link a saved farm project that already contains it"],
            "follow": "After these required details are supplied, the complete report can be generated immediately. Optional details can be refined later.",
            "suggested": ["Continue report", "Use a saved project"],
        },
        SI: {
            "labels": {"crop": "බෝගය", "location": "ස්ථානය", "area_value": "ඉඩම් ප්‍රමාණය"},
            "known_default": "ඔබගේ වාර්තා ඉලක්කය",
            "summary": "මට {known} දැනටමත් ලැබී ඇත. පහත වාර්තාව සෑදීමට අත්‍යවශ්‍ය තොරතුරු පමණක් අවශ්‍යයි. කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය සහ වගා දිනය නොදන්නා නම් ඒවා උපකල්පන ලෙස පැහැදිලිව දක්වා වාර්තාව ඉදිරියට ගෙන යන්න පුළුවන්.",
            "action": "පහත අත්‍යවශ්‍ය කොටස් පමණක් සම්පූර්ණ කරන්න. ඉන්පසු අමතර අනිවාර්ය popup නොමැතිව MihiMura වාර්තාව ඉදිරියට ගෙන යයි.",
            "why": "බෝගය, වගා ස්ථානය සහ ඉඩම් ප්‍රමාණය වගා, සම්පත් සහ මූල්‍ය ගණනයන්ගේ මූලික පරාසය තීරණය කරයි. අනෙක් තොරතුරු පසුව සකස් කළ හැකි උපකල්පන ලෙස තැබිය හැක.",
            "alternatives": ["අඩු තොරතුර සාමාන්‍ය chat එකෙන්ම ලබා දෙන්න", "එම ක්ෂේත්‍රයට අදාළ සුරකින ලද farm project එකක් සම්බන්ධ කරන්න"],
            "follow": "මෙම අත්‍යවශ්‍ය තොරතුරු ලැබුණු පසු සම්පූර්ණ වාර්තාව වහාම සකස් කළ හැක. අනෙක් තොරතුරු පසුව refine කළ හැක.",
            "suggested": ["වාර්තාව දිගටම", "සුරකින ලද project එකක් භාවිතා කරන්න"],
        },
        TA: {
            "labels": {"crop": "பயிர்", "location": "இடம்", "area_value": "நிலப்பரப்பு"},
            "known_default": "உங்கள் அறிக்கை நோக்கம்",
            "summary": "என்னிடம் ஏற்கனவே {known} உள்ளது. கீழே உள்ள அறிக்கையை உருவாக்கத் தேவையான கட்டாய விவரங்கள் மட்டும் வேண்டும். பருவம், பாசன மூலம், வகை மற்றும் நடவு தேதி தெரியாவிட்டால் அவற்றை தெளிவான கருதுகோள்களாகக் குறிப்பிட்டு அறிக்கையைத் தொடரலாம்.",
            "action": "கீழே உள்ள கட்டாய புலங்களை மட்டும் நிரப்பவும். அதன் பிறகு கூடுதல் கட்டாய popup இல்லாமல் MihiMura அறிக்கையைத் தொடரும்.",
            "why": "பயிர், சாகுபடி இடம் மற்றும் நிலப்பரப்பு தான் வேளாண்மை, வளம் மற்றும் நிதி கணக்கீட்டின் அடிப்படை பரப்பை நிர்ணயிக்கின்றன. மற்ற விவரங்களை பின்னர் திருத்தக்கூடிய கருதுகோள்களாக வைத்துக்கொள்ளலாம்.",
            "alternatives": ["காணாமல் உள்ள விவரத்தை சாதாரண chat-ல் எழுதவும்", "அதே வயலைச் சேர்ந்த சேமிக்கப்பட்ட farm project-ஐ இணைக்கவும்"],
            "follow": "இந்த கட்டாய விவரங்கள் கிடைத்ததும் முழு அறிக்கையை உடனே உருவாக்கலாம். மற்ற விவரங்களை பின்னர் refine செய்யலாம்.",
            "suggested": ["அறிக்கையை தொடரவும்", "சேமித்த project-ஐ பயன்படுத்தவும்"],
        },
    },
    # ---------------------------------------------------------- report: follow-ups
    "report_follow": {
        EN: {
            "detail": "No mandatory report details are missing. I already have crop={crop}, location={location}, and area={area}. Optional refinements still open: {optional}. I can keep these as explicit assumptions unless you want to refine them.",
            "detail_action": "Open the existing report, or refine one of the optional assumptions.",
            "equipment": "For this plan, the main equipment/resources are: {items}. The full report separates hire/own and method-dependent items.",
            "equipment_action": "Use the report equipment section to convert these into local quotations.",
            "finance": "The configured planning-base scenario for {area} {crop} currently uses estimated cost about LKR {cost:,}, revenue about LKR {revenue:,}, and profit about LKR {profit:,}. These are illustrative planning assumptions, not live quotations.",
            "finance_action": "Replace planning assumptions with current local input, labour, machinery and buyer quotations before investing.",
            "finance_missing": "A verified crop-specific financial scenario is not configured, so I will not invent a cost or profit figure.",
            "finance_missing_action": "Replace planning assumptions with current local quotations.",
            "market": "Selling channels to evaluate include: {items}. Buyer availability and prices must be refreshed close to harvest.",
            "market_action": "Collect current quotations and compare net price after transport, grading and payment terms.",
            "general": "This conversation is still using the {area} {crop} plan for {location}. I can answer follow-up questions about agronomy, equipment, inputs, costs/profit, harvest or marketing without restarting the report.",
            "general_action": "Ask about the report section you want to inspect or refine.",
            "why": "The report scenario is already stored in conversation memory, so MihiMura can answer section-level follow-ups without generating another PDF or asking for optional fields again.",
            "alternatives": ["Regenerate the report after changing assumptions", "Switch to Decision Support for a live operational decision"],
            "do_not": ["Do not treat illustrative planning prices as live market quotations", "Do not use unverified chemical or fertilizer rates"],
            "follow": "You can continue asking about any section of this same report.",
            "suggested": ["Ask about equipment", "Ask about costs & profit", "Ask about selling channels", "Refine assumptions"],
        },
        SI: {
            "detail": "අනිවාර්ය වාර්තා තොරතුරු කිසිවක් අඩු නැහැ. බෝගය={crop}, ස්ථානය={location}, ඉඩම් ප්‍රමාණය={area} ලෙස සුරැකී ඇත. තව refine කළ හැකි විස්තර: {optional}. ඒවා නොදන්නා නම් පැහැදිලි උපකල්පන ලෙස තබා ගන්නම්.",
            "detail_action": "පවතින වාර්තාව විවෘත කරන්න හෝ කැමති උපකල්පනයක් refine කරන්න.",
            "equipment": "මෙම සැලැස්මට ප්‍රධාන උපකරණ/සම්පත්: {items}. සම්පූර්ණ වාර්තාවේ කුලියට ගැනීම/අයිතිය සහ ක්‍රමය මත වෙනස්වන අයිතම වෙන වෙනම දක්වයි.",
            "equipment_action": "උපකරණ කොටස භාවිතා කර ප්‍රදේශීය මිල ගණන් එකතු කරන්න.",
            "finance": "{area} {crop} සඳහා දැනට configure කර ඇති planning-base scenario එකේ ඇස්තමේන්තු වියදම LKR {cost:,}, ආදායම LKR {revenue:,}, සහ ලාභය LKR {profit:,} පමණ වේ. මේවා සජීවී මිල ගණන් නොව planning estimates වේ.",
            "finance_action": "ආයෝජනයට පෙර ප්‍රදේශීය input, labour, machinery සහ buyer quotations වලින් මෙම උපකල්පන update කරන්න.",
            "finance_missing": "මෙම බෝගයට සත්‍යාපිත මූල්‍ය scenario එකක් configure කර නැති නිසා මම වියදමක් හෝ ලාභයක් හිතාගෙන නිර්මාණය කරන්නේ නැහැ.",
            "finance_missing_action": "වත්මන් ප්‍රදේශීය මිල ගණන් ලබාගෙන ගණනය නැවත කරන්න.",
            "market": "සලකා බැලිය හැකි අලෙවි නාලිකා: {items}. ගැනුම්කරුවන්ගේ ලබාගත හැකි බව සහ මිල අස්වැන්නට ආසන්නව නැවත තහවුරු කළ යුතුයි.",
            "market_action": "වත්මන් quotations එකතු කර ප්‍රවාහනය, grading සහ payment terms පසු net price එක සසඳන්න.",
            "general": "මෙම සංවාදය තවමත් {location} හි {area} {crop} සැලැස්ම භාවිතා කරයි. වාර්තාව නැවත ආරම්භ නොකර වගා, උපකරණ, inputs, වියදම්/ලාභ, අස්වැන්න හෝ අලෙවිය ගැන follow-up අහන්න පුළුවන්.",
            "general_action": "බලන්න හෝ refine කරන්න අවශ්‍ය වාර්තා කොටස අහන්න.",
            "why": "වාර්තා scenario එක conversation memory තුළ සුරැකී ඇති නිසා, නව PDF එකක් හෝ අනවශ්‍ය අමතර form නොමැතිව කොටස් මට්ටමේ follow-up වලට පිළිතුරු දිය හැක.",
            "alternatives": ["උපකල්පන වෙනස් කළ පසු වාර්තාව නැවත generate කරන්න", "සජීවී ක්ෂේත්‍ර තීරණයක් සඳහා Decision Support භාවිතා කරන්න"],
            "do_not": ["planning prices සජීවී market quotations ලෙස භාවිතා නොකරන්න", "තහවුරු නොකළ රසායනික/පොහොර rate භාවිතා නොකරන්න"],
            "follow": "මෙම වාර්තාවේ ඕනෑම කොටසක් ගැන මේ සංවාදයේම දිගටම අහන්න පුළුවන්.",
            "suggested": ["උපකරණ ගැන අහන්න", "වියදම් හා ලාභ ගැන අහන්න", "අලෙවි නාලිකා ගැන අහන්න", "උපකල්පන refine කරන්න"],
        },
        TA: {
            "detail": "கட்டாய அறிக்கை விவரங்கள் எதுவும் குறைவில்லை. பயிர்={crop}, இடம்={location}, நிலப்பரப்பு={area} என சேமிக்கப்பட்டுள்ளது. விருப்பமாக refine செய்யக்கூடியவை: {optional}. தெரியாவிட்டால் அவற்றை தெளிவான கருதுகோள்களாக வைத்துக்கொள்கிறேன்.",
            "detail_action": "தற்போதைய அறிக்கையைத் திறக்கவும் அல்லது ஒரு விருப்ப கருதுகோளை refine செய்யவும்.",
            "equipment": "இந்தத் திட்டத்தின் முக்கிய உபகரணங்கள்/வளங்கள்: {items}. முழு அறிக்கையில் வாடகை/சொந்தம் மற்றும் முறையைப் பொறுத்த பொருட்கள் தனித்தனியாக காட்டப்படும்.",
            "equipment_action": "உபகரணப் பகுதியைப் பயன்படுத்தி உள்ளூர் விலை மேற்கோள்களைச் சேகரிக்கவும்.",
            "finance": "{area} {crop} க்கான தற்போதைய planning-base scenario-வில் மதிப்பிடப்பட்ட செலவு சுமார் LKR {cost:,}, வருவாய் LKR {revenue:,}, லாபம் LKR {profit:,}. இவை நேரடி விலை மேற்கோள்கள் அல்ல; திட்டமிடல் மதிப்பீடுகள்.",
            "finance_action": "முதலீட்டுக்கு முன் உள்ளூர் input, labour, machinery மற்றும் buyer quotations மூலம் இவற்றை புதுப்பிக்கவும்.",
            "finance_missing": "இந்தப் பயிருக்கான சரிபார்க்கப்பட்ட நிதி scenario அமைக்கப்படவில்லை; எனவே செலவு அல்லது லாப எண்ணை நான் உருவாக்கமாட்டேன்.",
            "finance_missing_action": "தற்போதைய உள்ளூர் விலை மேற்கோள்களைப் பெற்று கணக்கை மீண்டும் செய்யவும்.",
            "market": "மதிப்பிட வேண்டிய விற்பனை வழிகள்: {items}. வாங்குபவர் கிடைப்பும் விலையும் அறுவடைக்கு அருகில் மீண்டும் சரிபார்க்க வேண்டும்.",
            "market_action": "தற்போதைய quotations சேகரித்து போக்குவரத்து, grading மற்றும் payment terms கழித்த net price-ஐ ஒப்பிடவும்.",
            "general": "இந்த உரையாடல் இன்னும் {location} பகுதியில் {area} {crop} திட்டத்தையே பயன்படுத்துகிறது. அறிக்கையை மீண்டும் தொடங்காமல் agronomy, equipment, inputs, செலவு/லாபம், அறுவடை அல்லது சந்தை பற்றி follow-up கேட்கலாம்.",
            "general_action": "பார்க்க அல்லது refine செய்ய வேண்டிய அறிக்கை பகுதியைக் கேளுங்கள்.",
            "why": "அறிக்கை scenario conversation memory-ல் சேமிக்கப்பட்டுள்ளதால், புதிய PDF அல்லது தேவையற்ற கூடுதல் form இல்லாமல் பகுதி அடிப்படையிலான follow-up கேள்விகளுக்கு பதிலளிக்கலாம்.",
            "alternatives": ["கருதுகோள்களை மாற்றிய பின் அறிக்கையை மீண்டும் உருவாக்கவும்", "நேரடி வயல் முடிவுக்கு Decision Support பயன்படுத்தவும்"],
            "do_not": ["planning prices-ஐ நேரடி market quotations என கருத வேண்டாம்", "சரிபார்க்காத chemical/fertilizer rate-ஐ பயன்படுத்த வேண்டாம்"],
            "follow": "இந்த அறிக்கையின் எந்தப் பகுதியைப் பற்றியும் இதே உரையாடலில் தொடர்ந்து கேட்கலாம்.",
            "suggested": ["உபகரணங்கள் பற்றி கேளுங்கள்", "செலவு & லாபம் பற்றி கேளுங்கள்", "விற்பனை வழிகள் பற்றி கேளுங்கள்", "கருதுகோள்களை refine செய்யவும்"],
        },
    },
    # -------------------------------------------------------------- report: ready
    "report_ready": {
        EN: {
            "assumptions": " Optional unknowns ({optional}) will be shown as assumptions/scenarios rather than blocking the report.",
            "assumptions_none": " The core and refinement details are already available.",
            "finance": " The current configured planning scenario gives a base profit estimate of about LKR {profit:,}, but this is not a live market quote and will be labelled as an estimate.",
            "finance_none": " Financial sections will identify the current data gaps instead of inventing prices.",
            "summary": "I have enough information to build the complete {area} {crop} report for {location}.{assumptions}{finance}",
            "action": "Generate the full report now with agronomy, equipment/tools, input planning, economics, risk, harvest and marketing sections.",
            "why": "Full Report mode uses a dedicated report planner instead of compressing a complex farm/business request into the short Decision Contract format.",
            "alternatives": ["Refine the season, irrigation, variety or planting date after generation", "Link a saved project to replace assumptions with actual field data"],
            "do_not": ["Do not treat illustrative cost, yield or selling-price scenarios as live quotations", "Do not use an unverified pesticide/fertilizer rate simply because it appears plausible"],
            "follow": "After generation, you can ask MihiMura to refine any section using actual quotations, a soil test, variety, irrigation details or buyer offers.",
            "suggested": ["Open full PDF", "Refine costs with local quotations", "Refine season / irrigation", "Create as farm project"],
        },
        SI: {
            "assumptions": " කන්නය/වාරි/ප්‍රභේදය/වගා දිනය වැනි අමතර තොරතුරු ({optional}) නොමැති නිසා ඒවා වාර්තාවේ පැහැදිලි උපකල්පන ලෙස දක්වනු ලැබේ.",
            "assumptions_none": " අවශ්‍ය මූලික සහ refine කරන තොරතුරු දැනටමත් ඇත.",
            "finance": " දැනට configure කර ඇති planning-base scenario එකේ ලාභ ඇස්තමේන්තුව LKR {profit:,} පමණයි; මෙය සජීවී market quotation එකක් නොව ඇස්තමේන්තුවක් ලෙස ලකුණු කරනු ඇත.",
            "finance_none": " මූල්‍ය කොටස මිල හිතාගෙන නිර්මාණය නොකර දත්ත හිස්තැන් පැහැදිලිව පෙන්වයි.",
            "summary": "{location} හි {area} {crop} සඳහා සම්පූර්ණ වගා වාර්තාව සකස් කිරීමට ප්‍රමාණවත් මූලික තොරතුරු මට ඇත.{assumptions}{finance}",
            "action": "වගා සැලැස්ම, උපකරණ/මෙවලම්, inputs, වියදම්-ලාභ, අවදානම්, අස්වැන්න සහ අලෙවිය ඇතුළත් සම්පූර්ණ වාර්තාව දැන් generate කරන්න.",
            "why": "Full Report mode එක සංකීර්ණ වගා සහ ව්‍යාපාර ඉල්ලීම කෙටි decision card එකකට සීමා නොකර වෙනම report planner workflow එකක් භාවිතා කරයි.",
            "alternatives": ["වාර්තාවෙන් පසු කන්නය, වාරි මූලාශ්‍රය, ප්‍රභේදය හෝ වගා දිනය refine කරන්න", "සත්‍ය field data භාවිතා කිරීමට saved project එකක් සම්බන්ධ කරන්න"],
            "do_not": ["planning cost/yield/selling-price scenarios සජීවී quotations ලෙස සලකන්න එපා", "තහවුරු නොකළ pesticide/fertilizer rate භාවිතා නොකරන්න"],
            "follow": "වාර්තාව generate කළ පසු actual quotations, soil test, variety, irrigation details හෝ buyer offers භාවිතා කර ඕනෑම කොටසක් refine කරන්න පුළුවන්.",
            "suggested": ["සම්පූර්ණ PDF විවෘත කරන්න", "ප්‍රදේශීය quotations වලින් වියදම් refine කරන්න", "කන්නය / වාරි තොරතුරු refine කරන්න", "farm project එකක් ලෙස සාදන්න"],
        },
        TA: {
            "assumptions": " பருவம்/பாசனம்/வகை/நடவு தேதி போன்ற விருப்ப விவரங்கள் ({optional}) இல்லாததால் அவை அறிக்கையில் தெளிவான கருதுகோள்களாகக் காட்டப்படும்.",
            "assumptions_none": " தேவையான அடிப்படை மற்றும் refinement விவரங்கள் ஏற்கனவே உள்ளன.",
            "finance": " தற்போதைய planning-base scenario சுமார் LKR {profit:,} லாபத்தை மதிப்பிடுகிறது; இது நேரடி market quotation அல்ல, estimate என்று தெளிவாக குறிக்கப்படும்.",
            "finance_none": " நிதிப் பகுதி விலைகளை உருவாக்காமல் உள்ள data gaps-ஐ தெளிவாகக் காட்டும்.",
            "summary": "{location} பகுதியில் {area} {crop} க்கான முழுமையான சாகுபடி அறிக்கையை உருவாக்கத் தேவையான அடிப்படை தகவல் உள்ளது.{assumptions}{finance}",
            "action": "சாகுபடி திட்டம், உபகரணங்கள்/கருவிகள், inputs, செலவு-லாபம், அபாயம், அறுவடை மற்றும் சந்தைப்படுத்தலை உள்ளடக்கிய முழு அறிக்கையை இப்போது உருவாக்கவும்.",
            "why": "Full Report mode சிக்கலான சாகுபடி/வணிக கோரிக்கையை குறுகிய decision card-ஆக சுருக்காமல் தனிப்பட்ட report planner workflow-ஐ பயன்படுத்துகிறது.",
            "alternatives": ["அறிக்கை உருவான பின் பருவம், பாசனம், வகை அல்லது நடவு தேதியை refine செய்யவும்", "உண்மையான வயல் தரவைப் பயன்படுத்த saved project-ஐ இணைக்கவும்"],
            "do_not": ["planning cost/yield/selling-price scenarios-ஐ நேரடி quotations என கருத வேண்டாம்", "சரிபார்க்கப்படாத pesticide/fertilizer rate-ஐ பயன்படுத்த வேண்டாம்"],
            "follow": "அறிக்கை உருவான பின் actual quotations, soil test, variety, irrigation details அல்லது buyer offers மூலம் எந்தப் பகுதியையும் refine செய்யலாம்.",
            "suggested": ["முழு PDF-ஐ திறக்கவும்", "உள்ளூர் quotations மூலம் செலவுகளை refine செய்யவும்", "பருவம் / பாசனத்தை refine செய்யவும்", "farm project ஆக உருவாக்கவும்"],
        },
    },
    # ---------------------------------------------------- simple chat (no model)
    "chat_fallback": {
        EN: {
            "greeting": "Hello. I’m MihiMura. You can ask a general agriculture question here, or use Decision Support for live farm/weather decisions and Full Report for complete cultivation and business planning.",
            "general": "I can discuss this in Simple Chat using general agricultural knowledge and the context of this conversation. For a live farm decision, switch to Decision Support; for a comprehensive cultivation/cost/profit/marketing plan, use Full Report.",
            "action": "Continue the conversation",
            "why": "Simple Chat intentionally avoids unnecessary live-data and safety-tool calls.",
            "follow": "Ask naturally; the intent router will tell you when another mode is a better fit.",
            "suggested": ["Ask a general farming question", "Use Decision Support", "Create a Full Report"],
            "greeting_words": ("hi", "hello", "hey"),
        },
        SI: {
            "greeting": "ආයුබෝවන්. මම MihiMura. සාමාන්‍ය කෘෂිකාර්මික ප්‍රශ්න මෙහි අහන්න පුළුවන්. සජීවී කාලගුණ/ක්ෂේත්‍ර තීරණ සඳහා Decision Support සහ සම්පූර්ණ වගා-ව්‍යාපාර සැලසුමක් සඳහා Full Report භාවිතා කරන්න.",
            "general": "මෙය Simple Chat තුළ සාමාන්‍ය කෘෂිකාර්මික දැනුම සහ මේ සංවාදයේ පසුබිම භාවිතා කර පැහැදිලි කළ හැක. සජීවී ක්ෂේත්‍ර තීරණයක් නම් Decision Support භාවිතා කරන්න; වියදම්, ලාභ සහ අලෙවිය ඇතුළත් සම්පූර්ණ සැලසුමක් නම් Full Report භාවිතා කරන්න.",
            "action": "සංවාදය දිගටම කරගෙන යන්න",
            "why": "Simple Chat අනවශ්‍ය සජීවී දත්ත සහ ආරක්ෂක tool calls නොකරයි.",
            "follow": "ස්වභාවිකව ප්‍රශ්නය අහන්න; වෙනත් mode එකක් වඩා සුදුසු නම් intent router එක දැනුම් දෙයි.",
            "suggested": ["සාමාන්‍ය ගොවිතැන් ප්‍රශ්නයක් අහන්න", "Decision Support භාවිතා කරන්න", "Full Report එකක් සකස් කරන්න"],
            "greeting_words": ("ආයුබෝවන්", "හෙලෝ"),
        },
        TA: {
            "greeting": "வணக்கம். நான் MihiMura. பொதுவான வேளாண்மை கேள்விகளை இங்கே கேட்கலாம். நேரடி வானிலை/வயல் முடிவுகளுக்கு Decision Support-ஐவும், முழுமையான சாகுபடி-வணிகத் திட்டத்திற்கு Full Report-ஐவும் பயன்படுத்தலாம்.",
            "general": "இதைக் Simple Chat-ல் பொதுவான வேளாண்மை அறிவும் இந்த உரையாடலின் சூழலும் பயன்படுத்தி விளக்கலாம். நேரடி வயல் முடிவு வேண்டுமெனில் Decision Support-ஐ பயன்படுத்தவும்; செலவு, லாபம் மற்றும் சந்தைப்படுத்தலுடன் முழுமையான திட்டம் வேண்டுமெனில் Full Report-ஐ பயன்படுத்தவும்.",
            "action": "உரையாடலைத் தொடரவும்",
            "why": "Simple Chat தேவையற்ற நேரடி தரவு மற்றும் safety tool calls-ஐ தவிர்க்கிறது.",
            "follow": "இயல்பாக கேளுங்கள்; வேறு mode சிறந்தது என்றால் intent router பரிந்துரைக்கும்.",
            "suggested": ["பொதுவான வேளாண்மை கேள்வி கேளுங்கள்", "Decision Support பயன்படுத்தவும்", "Full Report உருவாக்கவும்"],
            "greeting_words": ("வணக்கம்", "ஹலோ"),
        },
    },
    # ------------------------------------------------ decision support (no model)
    "decision_fallback": {
        EN: {
            "weather_live": "For {location}, Open-Meteo currently reports about {temp}°C, {humidity}% humidity, wind {wind} km/h and precipitation {precip} mm.",
            "weather_live_why": "This uses live coordinate-based weather evidence for the resolved location. Check the next-day forecast as well before a weather-sensitive field operation.",
            "location_default": "the resolved location",
            "market_price": "Use fresh buyer quotations before setting a selling price; this local build does not yet have a verified live market-price feed.",
            "market_price_why": "MihiMura can identify selling-channel categories, but it must not invent a current crop price when no live verified price connector was checked.",
            "market_channels": "Compare current quotations across relevant selling channels before committing the harvest.",
            "market_channels_why": "Available channel categories include: {channels}. Specific buyers and prices must be verified close to sale.",
            "fertilizer_rain": "Delay the exposed fertilizer task and re-check the next lower-rain operating window against the current approved crop protocol.",
            "fertilizer_rain_why": "The next-day forecast rain probability is about {rain:.0f}% for the resolved location, which can increase runoff or nutrient-loss risk. The exact application rate is intentionally not generated.",
            "rate_sensitive": "Do not select a chemical or dose from this chat alone. Confirm the crop, target problem and current approved label/protocol, and escalate if the condition is uncertain.",
            "rate_sensitive_why": "This request is rate- or treatment-sensitive, so MihiMura applies a deterministic safety gate before any model explanation.",
            "weather_unavailable": "Confirm the farm/location coordinates and retry before treating this as a live weather decision.",
            "weather_unavailable_why": "Decision Support will not pretend to have checked current weather when the live weather API did not return usable data.",
            "general": "Use the current farm/scenario evidence before changing the field operation.",
            "general_why": "Decision Support used only the evidence tools selected for this intent, together with the active conversation and farm context.",
            "alternatives": ["Record another field observation before treatment", "Ask an agricultural instructor to review the evidence package"],
            "alternatives_market": ["Compare cooperative/processor quotations", "Record buyer offers in the farm project"],
            "do_not": ["Do not treat an uncertain image result as a confirmed diagnosis", "Do not use an invented chemical or fertilizer dose"],
            "do_not_market": ["Do not present an old or unverified price as today's market price", "Do not compare offers without accounting for grade, transport and payment terms"],
            "follow": "Continue in this same conversation; MihiMura will retain the active scenario.",
            "suggested": ["Explain the reasoning", "Check next 14 days"],
            "suggested_market": ["Show selling channels", "Compare buyer quotations", "Create a full marketing report"],
            "counter": "Different field evidence, a corrected location, crop stage, forecast or current buyer quotation can change the recommendation.",
        },
        SI: {
            "weather_live": "{location} සඳහා දැනට උෂ්ණත්වය {temp}°C, ආර්ද්‍රතාව {humidity}%, සුළං වේගය {wind} km/h සහ වර්ෂාපතනය {precip} mm ලෙස Open-Meteo දත්ත පෙන්වයි.",
            "weather_live_why": "මෙය වත්මන් සම්බන්ධීකරණ අනුව ලබාගත් සජීවී කාලගුණ දත්ත මත පදනම් වේ. ක්ෂේත්‍ර ක්‍රියාවක් කිරීමට පෙර ඉදිරි දින අනාවැකියද බලන්න.",
            "location_default": "the resolved location",
            "market_price": "විකුණුම් මිල තීරණය කිරීමට පෙර වත්මන් ගැනුම්කරුවන්ගෙන් quotations ලබාගන්න. මෙම local build එකට තවම සත්‍යාපිත live market-price feed එකක් සම්බන්ධ කර නැහැ.",
            "market_price_why": "MihiMura අලෙවි නාලිකා හඳුනාගත හැකි නමුත් සජීවී සත්‍යාපිත මිල දත්ත නොමැති විට අද බෝග මිලක් හිතාගෙන ප්‍රකාශ නොකරයි.",
            "market_channels": "අස්වැන්න විකිණීමට පෙර අදාළ අලෙවි නාලිකා කිහිපයක වත්මන් quotations සසඳන්න.",
            "market_channels_why": "සලකා බැලිය හැකි නාලිකා: {channels}. නිශ්චිත ගැනුම්කරුවන් සහ මිල අස්වැන්නට ආසන්නව නැවත තහවුරු කළ යුතුයි.",
            "fertilizer_rain": "වැසි අවදානම වැඩි නිසා විවෘත පොහොර යෙදීම තාවකාලිකව කල් දමා, අඩු වැසි කවුළුවක් ලැබෙන විට වත්මන් අනුමත බෝග උපදෙස් සමඟ නැවත පරීක්ෂා කරන්න.",
            "fertilizer_rain_why": "හෙට සඳහා අනාවැකි වැසි සම්භාවිතාව සම්භාව්‍යයෙන් {rain:.0f}% පමණයි. එය runoff හෝ nutrient-loss අවදානම වැඩි කළ හැක. නිශ්චිත පොහොර rate එක මෙහි හිතාගෙන නිර්මාණය කරන්නේ නැහැ.",
            "rate_sensitive": "මෙම chat එක පමණක් භාවිතා කර රසායනිකයක් හෝ dose එකක් තෝරා නොගන්න. බෝගය, ඉලක්ක රෝග/පළිබෝධය සහ වත්මන් අනුමත label/protocol එක තහවුරු කරන්න; සැකයක් තිබේ නම් විශේෂඥයෙකු වෙත යොමු කරන්න.",
            "rate_sensitive_why": "මෙය rate/treatment-sensitive ඉල්ලීමක් නිසා model explanation එකට පෙර MihiMura deterministic safety gate එක ක්‍රියාත්මක කරයි.",
            "weather_unavailable": "සජීවී කාලගුණ තීරණයක් සඳහා නිවැරදි ස්ථානය/coordinates තහවුරු කර නැවත උත්සාහ කරන්න.",
            "weather_unavailable_why": "Decision Support වත්මන් කාලගුණ API දත්ත සාර්ථකව ලැබී නැති විට සජීවී කාලගුණය පරීක්ෂා කළා යැයි පෙන්වන්නේ නැහැ.",
            "general": "ක්ෂේත්‍ර ක්‍රියාව වෙනස් කිරීමට පෙර වත්මන් farm/scenario evidence භාවිතා කරන්න.",
            "general_why": "Decision Support මෙම intent එකට අදාළ ලෙස තෝරාගත් evidence tools සහ සක්‍රීය සංවාද/farm context පමණක් භාවිතා කළා.",
            "alternatives": ["තවත් field observation එකක් සටහන් කරන්න", "evidence package එක කෘෂිකර්ම උපදේශකයෙකුගෙන් review කරගන්න"],
            "alternatives_market": ["සමූපකාර/processor quotations සසඳන්න", "buyer offers farm project එකේ සටහන් කරන්න"],
            "do_not": ["අනිශ්චිත image result එක confirmed diagnosis එකක් ලෙස සලකන්න එපා", "හිතාගෙන නිර්මාණය කළ chemical/fertilizer dose භාවිතා නොකරන්න"],
            "do_not_market": ["පරණ හෝ තහවුරු නොකළ මිල අද market price ලෙස පෙන්වන්න එපා", "grade, transport සහ payment terms නොසලකා offers සසඳන්න එපා"],
            "follow": "මෙම සංවාදයේම දිගටම අහන්න; MihiMura සක්‍රීය scenario එක මතක තබා ගනී.",
            "suggested": ["හේතුව පැහැදිලි කරන්න", "ඉදිරි දින 14 බලන්න"],
            "suggested_market": ["අලෙවි නාලිකා පෙන්වන්න", "buyer quotations සසඳන්න", "සම්පූර්ණ marketing report එකක් සාදන්න"],
            "counter": "ක්ෂේත්‍ර තොරතුරු, forecast, protocol හෝ market evidence වෙනස් වුවහොත් නිර්දේශයද වෙනස් විය හැක.",
        },
        TA: {
            "weather_live": "{location} பகுதியில் தற்போது வெப்பநிலை {temp}°C, ஈரப்பதம் {humidity}%, காற்றின் வேகம் {wind} km/h மற்றும் மழைப்பொழிவு {precip} mm என Open-Meteo தரவு காட்டுகிறது.",
            "weather_live_why": "இது தீர்மானிக்கப்பட்ட இருப்பிடத்தின் நேரடி வானிலைத் தரவை அடிப்படையாகக் கொண்டது. வயல் நடவடிக்கைக்கு முன் அடுத்த நாட்களின் முன்னறிவிப்பையும் சரிபார்க்கவும்.",
            "location_default": "the resolved location",
            "market_price": "விற்பனை விலையை நிர்ணயிக்கும் முன் தற்போதைய வாங்குபவர் quotations-ஐ பெறவும். இந்த local build-ல் இன்னும் சரிபார்க்கப்பட்ட live market-price feed இணைக்கப்படவில்லை.",
            "market_price_why": "MihiMura விற்பனை வழிகளை அடையாளம் காண முடியும்; ஆனால் சரிபார்க்கப்பட்ட நேரடி விலை feed இல்லாதபோது இன்றைய பயிர் விலையை உருவாக்காது.",
            "market_channels": "அறுவடையை விற்கும் முன் தொடர்புடைய பல விற்பனை வழிகளின் தற்போதைய quotations-ஐ ஒப்பிடவும்.",
            "market_channels_why": "பரிசீலிக்கக்கூடிய வழிகள்: {channels}. குறிப்பிட்ட வாங்குபவர்களும் விலைகளும் விற்பனைக்கு அருகில் மீண்டும் சரிபார்க்கப்பட வேண்டும்.",
            "fertilizer_rain": "மழை அபாயம் அதிகமாக இருப்பதால் வெளிப்புற உரப் பயன்பாட்டை தற்காலிகமாக ஒத்திவைத்து, குறைந்த மழை நேரத்தில் தற்போதைய அங்கீகரிக்கப்பட்ட பயிர் வழிகாட்டுதலுடன் மீண்டும் சரிபார்க்கவும்.",
            "fertilizer_rain_why": "நாளைய முன்னறிவிப்பு மழை சாத்தியம் சுமார் {rain:.0f}%. இது runoff அல்லது nutrient-loss அபாயத்தை அதிகரிக்கலாம். துல்லியமான உர அளவு இங்கே உருவாக்கப்படாது.",
            "rate_sensitive": "இந்த chat மட்டும் வைத்து chemical அல்லது dose-ஐ தேர்வு செய்ய வேண்டாம். பயிர், இலக்கு பிரச்சினை மற்றும் தற்போதைய அங்கீகரிக்கப்பட்ட label/protocol-ஐ உறுதிப்படுத்தவும்; சந்தேகம் இருந்தால் நிபுணரிடம் ஆலோசிக்கவும்.",
            "rate_sensitive_why": "இது rate/treatment-sensitive கோரிக்கை என்பதால் model விளக்கத்திற்கு முன் MihiMura deterministic safety gate-ஐ பயன்படுத்துகிறது.",
            "weather_unavailable": "நேரடி வானிலை முடிவுக்கு சரியான இடம்/coordinates-ஐ உறுதிப்படுத்தி மீண்டும் முயற்சிக்கவும்.",
            "weather_unavailable_why": "தற்போதைய வானிலை API தரவு வெற்றிகரமாக கிடைக்காதபோது Decision Support நேரடி வானிலை சரிபார்க்கப்பட்டது என்று கூறாது.",
            "general": "வயல் நடவடிக்கையை மாற்றும் முன் தற்போதைய farm/scenario evidence-ஐ பயன்படுத்தவும்.",
            "general_why": "Decision Support இந்த intent-க்கு தேர்ந்தெடுக்கப்பட்ட evidence tools மற்றும் செயலில் உள்ள conversation/farm context-ஐ மட்டுமே பயன்படுத்தியது.",
            "alternatives": ["மேலும் ஒரு field observation பதிவு செய்யவும்", "evidence package-ஐ வேளாண்மை ஆலோசகரிடம் review செய்யவும்"],
            "alternatives_market": ["கூட்டுறவு/processor quotations-ஐ ஒப்பிடவும்", "buyer offers-ஐ farm project-ல் பதிவு செய்யவும்"],
            "do_not": ["தெளிவில்லாத image result-ஐ confirmed diagnosis என கருத வேண்டாம்", "உருவாக்கப்பட்ட chemical/fertilizer dose-ஐ பயன்படுத்த வேண்டாம்"],
            "do_not_market": ["பழைய அல்லது சரிபார்க்காத விலையை இன்றைய market price என காட்ட வேண்டாம்", "grade, transport மற்றும் payment terms-ஐ தவிர்த்து offers-ஐ ஒப்பிட வேண்டாம்"],
            "follow": "இதே உரையாடலில் தொடரவும்; MihiMura செயலில் உள்ள scenario-ஐ நினைவில் வைத்திருக்கும்.",
            "suggested": ["காரணத்தை விளக்கவும்", "அடுத்த 14 நாட்களை பார்க்கவும்"],
            "suggested_market": ["விற்பனை வழிகளை காட்டவும்", "buyer quotations ஒப்பிடவும்", "முழு marketing report உருவாக்கவும்"],
            "counter": "வயல் தகவல், forecast, protocol அல்லது market evidence மாறினால் பரிந்துரையும் மாறலாம்.",
        },
    },
    # ----------------------------------------- full report generated (endpoint)
    "report_generated": {
        EN: {
            "ready": "The complete report has now been generated and stored privately. Open the PDF for the full agronomy, equipment/tools, input, cost/profit, harvest and marketing plan.",
            "action": "Open the generated report, then refine any estimate with actual local quotations or field evidence.",
            "failed": "The report content is ready, but PDF generation could not complete in this request.",
        },
        SI: {
            "ready": "සම්පූර්ණ වාර්තාව දැන් සකස් කර පුද්ගලිකව ගබඩා කර ඇත. සම්පූර්ණ වගා, උපකරණ/මෙවලම්, ආදාන, වියදම්/ලාභ, අස්වැන්න සහ අලෙවි සැලැස්ම සඳහා PDF එක විවෘත කරන්න.",
            "action": "සකස් කළ වාර්තාව විවෘත කර, සැබෑ දේශීය මිල ගණන් හෝ ක්ෂේත්‍ර දත්ත ලැබුණු විට ඇස්තමේන්තු යාවත්කාලීන කරන්න.",
            "failed": "වාර්තා අන්තර්ගතය සූදානම් නමුත් මෙම ඉල්ලීමේදී PDF එක සම්පූර්ණ කිරීමට නොහැකි විය.",
        },
        TA: {
            "ready": "முழுமையான அறிக்கை இப்போது உருவாக்கப்பட்டு தனிப்பட்ட முறையில் சேமிக்கப்பட்டுள்ளது. முழு சாகுபடி, உபகரணங்கள்/கருவிகள், உள்ளீடுகள், செலவு/லாபம், அறுவடை மற்றும் சந்தைப்படுத்தல் திட்டத்திற்காக PDF-ஐ திறக்கவும்.",
            "action": "உருவாக்கப்பட்ட அறிக்கையை திறந்து, உண்மையான உள்ளூர் விலைப்புள்ளிகள் அல்லது வயல் தரவு கிடைக்கும் போது மதிப்பீடுகளை புதுப்பிக்கவும்.",
            "failed": "அறிக்கை உள்ளடக்கம் தயாராக உள்ளது; ஆனால் இந்த கோரிக்கையில் PDF உருவாக்கத்தை முடிக்க முடியவில்லை.",
        },
    },
    # -------------------------------------------- generic defaults for any reply
    "defaults": {
        EN: {
            "summary": "Review the evidence before acting.",
            "why": "The recommendation is based on the available project, conversation and selected evidence tools.",
            "follow_up": "Continue in this conversation or re-check after conditions change.",
            "counterfactual": "Materially different field, forecast, protocol or market evidence can change this recommendation.",
        },
        SI: {
            "summary": "ක්‍රියා කිරීමට පෙර ලබාගත හැකි evidence සමාලෝචනය කරන්න.",
            "why": "නිර්දේශය ලබාගත හැකි project, conversation සහ තෝරාගත් evidence tools මත පදනම් වේ.",
            "follow_up": "මෙම සංවාදයේම දිගටම අහන්න හෝ තත්ත්වය වෙනස් වූ පසු නැවත පරීක්ෂා කරන්න.",
            "counterfactual": "ක්ෂේත්‍ර තොරතුරු, forecast, protocol හෝ market evidence වෙනස් වුවහොත් නිර්දේශයද වෙනස් විය හැක.",
        },
        TA: {
            "summary": "நடவடிக்கை எடுக்கும் முன் கிடைக்கக்கூடிய evidence-ஐ பரிசீலிக்கவும்.",
            "why": "பரிந்துரை கிடைக்கக்கூடிய project, conversation மற்றும் தேர்ந்தெடுக்கப்பட்ட evidence tools அடிப்படையில் உருவாக்கப்பட்டது.",
            "follow_up": "இதே உரையாடலில் தொடரவும் அல்லது நிலை மாறிய பின் மீண்டும் சரிபார்க்கவும்.",
            "counterfactual": "வயல் தகவல், forecast, protocol அல்லது market evidence மாறினால் பரிந்துரையும் மாறலாம்.",
        },
    },
}


def bundle(section: str, language: Any) -> dict[str, Any]:
    """All strings of one section in the requested language."""
    return TEXT[section][normalize_language(language)]


def t(section: str, key: str, language: Any, **values: Any) -> Any:
    """One string (formatted with ``values``) or list in the requested language."""
    value = bundle(section, language)[key]
    if isinstance(value, str) and values:
        return value.format(**values)
    return value
