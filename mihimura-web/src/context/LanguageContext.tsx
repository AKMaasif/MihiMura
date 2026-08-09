import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react';
import { platformApi } from '../services/platformApi';
import { useAuth } from './AuthContext';

export type AppLanguage = 'English' | 'Sinhala' | 'Tamil';

type LanguageContextValue = {
  language: AppLanguage;
  locale: string;
  shortCode: string;
  changing: boolean;
  setLanguage: (language: AppLanguage) => Promise<void>;
  t: (key: string) => string;
};

const translations: Record<AppLanguage, Record<string, string>> = {
  English: {
    today: 'Today', intelligence: 'Intelligence', aiSupport: 'AI support', farmManagement: 'Farm management', commerce: 'Commerce', insights: 'Insights', professional: 'Professional',
    dashboard: 'Dashboard', nationalIntelligence: 'National intelligence', localSituation: 'Local situation', riskDisaster: 'Risk & disaster', disasterMap: 'Disaster map', satelliteView: 'Satellite view', communitySentinel: 'Community sentinel', mihiMuraAI: 'MihiMura AI', cropHealthScan: 'Crop health scan', recommendationHistory: 'Recommendation history', expertEscalation: 'Expert escalation', myFarms: 'My farms', farmMap: 'Farm map', projects: 'Projects', tasks: 'Tasks', fieldDiary: 'Field diary', expenses: 'Expenses', harvest: 'Harvest', verifiedProducts: 'Verified products', suppliers: 'Suppliers', compare: 'Compare', cart: 'Cart', ordersTracking: 'Orders & tracking', reportsImpact: 'Reports & impact', settingsPrivacy: 'Settings & privacy', agronomistConsole: 'Agronomist console', cooperativePortal: 'Cooperative portal', govAnalytics: 'Gov / NGO analytics', administration: 'Administration',
    activeRegion: 'Active region', liveDecisionSupport: 'Live decision support', preferences: 'Preferences', signOut: 'Sign out', sriLanka: 'Sri Lanka',
    searchPlaceholder: 'Search field, task, crop…', search: 'Search', noSearchResults: 'No matching farms, projects, tasks or pages.', pages: 'Pages', farms: 'Farms', cropProjects: 'Crop projects', taskResults: 'Tasks',
    language: 'Language', english: 'English', sinhala: 'සිංහල', tamil: 'தமிழ்', savingLanguage: 'Saving…',
    notifications: 'Notifications', markAllRead: 'Mark all read', noNotifications: 'No notifications yet.', allCaughtUp: 'You’re all caught up.', scheduled: 'Scheduled', openTasks: 'Open task centre',
    farmer: 'farmer',
    title_dashboard:'Farmer Command Centre', title_overview:'National Intelligence Centre', title_local:'Local Situation', title_climate:'Climate & Disaster Risk Centre', title_disasterMap:'Disaster Map', title_satellite:'Satellite Intelligence', title_community:'Community Sentinel', title_ai:'MihiMura AI', title_scan:'Crop Health Scan', title_recommendations:'Recommendation History', title_expert:'Expert Escalation', title_farms:'My Farms', title_farmMap:'Farm Map', title_projects:'Cultivation Projects', title_tasks:'Task & Notification Centre', title_diary:'Field Diary', title_expenses:'Expenses', title_harvest:'Harvest & Season Review', title_marketplace:'Verified Marketplace', title_suppliers:'Verified Suppliers', title_compare:'Product Comparison', title_cart:'Cart & Confirmation', title_orders:'Orders & Delivery', title_reports:'Reports & SDG Impact', title_settings:'Profile, Privacy & Accessibility', title_agronomist:'Agronomist Console', title_cooperative:'Cooperative / Supplier Portal', title_government:'Government / NGO Analytics', title_admin:'Administration & Data Operations',
  },
  Sinhala: {
    today: 'අද', intelligence: 'බුද්ධි තොරතුරු', aiSupport: 'AI සහාය', farmManagement: 'ගොවිපල කළමනාකරණය', commerce: 'වෙළඳ සේවා', insights: 'වාර්තා', professional: 'වෘත්තීය',
    dashboard: 'ප්‍රධාන පුවරුව', nationalIntelligence: 'ජාතික කෘෂි තොරතුරු', localSituation: 'ප්‍රාදේශීය තත්ත්වය', riskDisaster: 'අවදානම් හා ආපදා', disasterMap: 'ආපදා සිතියම', satelliteView: 'චන්ද්‍රිකා දර්ශනය', communitySentinel: 'ප්‍රජා නිරීක්ෂණය', mihiMuraAI: 'MihiMura AI', cropHealthScan: 'බෝග සෞඛ්‍ය පරීක්ෂාව', recommendationHistory: 'නිර්දේශ ඉතිහාසය', expertEscalation: 'විශේෂඥ වෙත යොමු කිරීම', myFarms: 'මගේ ගොවිපල', farmMap: 'ගොවිපල සිතියම', projects: 'වගා ව්‍යාපෘති', tasks: 'කාර්යයන්', fieldDiary: 'ක්ෂේත්‍ර දිනපොත', expenses: 'වියදම්', harvest: 'අස්වැන්න', verifiedProducts: 'තහවුරු කළ නිෂ්පාදන', suppliers: 'සැපයුම්කරුවන්', compare: 'සසඳන්න', cart: 'කරත්තය', ordersTracking: 'ඇණවුම් හා ලුහුබැඳීම', reportsImpact: 'වාර්තා හා බලපෑම', settingsPrivacy: 'සැකසුම් හා පෞද්ගලිකත්වය', agronomistConsole: 'කෘෂි විශේෂඥ පුවරුව', cooperativePortal: 'සමූපකාර පෝර්ටලය', govAnalytics: 'රජය / NGO විශ්ලේෂණ', administration: 'පරිපාලනය',
    activeRegion: 'ක්‍රියාකාරී ප්‍රදේශය', liveDecisionSupport: 'සජීවී තීරණ සහාය', preferences: 'මනාප', signOut: 'පිටවන්න', sriLanka: 'ශ්‍රී ලංකාව',
    searchPlaceholder: 'ක්ෂේත්‍ර, කාර්ය, බෝග සොයන්න…', search: 'සොයන්න', noSearchResults: 'ගැළපෙන ගොවිපල, ව්‍යාපෘති, කාර්ය හෝ පිටු නොමැත.', pages: 'පිටු', farms: 'ගොවිපල', cropProjects: 'බෝග ව්‍යාපෘති', taskResults: 'කාර්යයන්',
    language: 'භාෂාව', english: 'English', sinhala: 'සිංහල', tamil: 'தமிழ்', savingLanguage: 'සුරකිමින්…',
    notifications: 'දැනුම්දීම්', markAllRead: 'සියල්ල කියවූ ලෙස සලකන්න', noNotifications: 'තවම දැනුම්දීම් නොමැත.', allCaughtUp: 'නව දැනුම්දීමක් නොමැත.', scheduled: 'නියමිත', openTasks: 'කාර්ය මධ්‍යස්ථානය විවෘත කරන්න',
    farmer: 'ගොවියා',
    title_dashboard:'ගොවි තීරණ මධ්‍යස්ථානය', title_overview:'ජාතික කෘෂි බුද්ධි මධ්‍යස්ථානය', title_local:'ප්‍රාදේශීය තත්ත්වය', title_climate:'දේශගුණ හා ආපදා අවදානම් මධ්‍යස්ථානය', title_disasterMap:'ආපදා සිතියම', title_satellite:'චන්ද්‍රිකා තොරතුරු', title_community:'ප්‍රජා නිරීක්ෂණය', title_ai:'MihiMura AI', title_scan:'බෝග සෞඛ්‍ය පරීක්ෂාව', title_recommendations:'නිර්දේශ ඉතිහාසය', title_expert:'විශේෂඥ වෙත යොමු කිරීම', title_farms:'මගේ ගොවිපල', title_farmMap:'ගොවිපල සිතියම', title_projects:'වගා ව්‍යාපෘති', title_tasks:'කාර්ය හා දැනුම්දීම් මධ්‍යස්ථානය', title_diary:'ක්ෂේත්‍ර දිනපොත', title_expenses:'වියදම්', title_harvest:'අස්වැන්න හා වාර සමාලෝචනය', title_marketplace:'තහවුරු කළ වෙළඳපොළ', title_suppliers:'තහවුරු කළ සැපයුම්කරුවන්', title_compare:'නිෂ්පාදන සසඳීම', title_cart:'කරත්තය හා තහවුරු කිරීම', title_orders:'ඇණවුම් හා බෙදාහැරීම', title_reports:'වාර්තා හා SDG බලපෑම', title_settings:'පැතිකඩ, පෞද්ගලිකත්වය හා ප්‍රවේශතාව', title_agronomist:'කෘෂි විශේෂඥ පුවරුව', title_cooperative:'සමූපකාර / සැපයුම්කරු පෝර්ටලය', title_government:'රජය / NGO විශ්ලේෂණ', title_admin:'පරිපාලන හා දත්ත මෙහෙයුම්',
  },
  Tamil: {
    today: 'இன்று', intelligence: 'நுண்ணறிவு', aiSupport: 'AI உதவி', farmManagement: 'பண்ணை மேலாண்மை', commerce: 'வணிகம்', insights: 'அறிக்கைகள்', professional: 'தொழில்முறை',
    dashboard: 'முகப்புப் பலகை', nationalIntelligence: 'தேசிய வேளாண் நுண்ணறிவு', localSituation: 'உள்ளூர் நிலை', riskDisaster: 'ஆபத்து & பேரிடர்', disasterMap: 'பேரிடர் வரைபடம்', satelliteView: 'செயற்கைக்கோள் பார்வை', communitySentinel: 'சமூக கண்காணிப்பு', mihiMuraAI: 'MihiMura AI', cropHealthScan: 'பயிர் நல ஸ்கேன்', recommendationHistory: 'பரிந்துரை வரலாறு', expertEscalation: 'நிபுணர் பரிந்துரை', myFarms: 'என் பண்ணைகள்', farmMap: 'பண்ணை வரைபடம்', projects: 'சாகுபடி திட்டங்கள்', tasks: 'பணிகள்', fieldDiary: 'வயல் பதிவேடு', expenses: 'செலவுகள்', harvest: 'அறுவடை', verifiedProducts: 'சரிபார்க்கப்பட்ட பொருட்கள்', suppliers: 'விநியோகஸ்தர்கள்', compare: 'ஒப்பிடு', cart: 'கூடை', ordersTracking: 'ஆர்டர்கள் & கண்காணிப்பு', reportsImpact: 'அறிக்கைகள் & தாக்கம்', settingsPrivacy: 'அமைப்புகள் & தனியுரிமை', agronomistConsole: 'வேளாண் நிபுணர் கன்சோல்', cooperativePortal: 'கூட்டுறவு போர்டல்', govAnalytics: 'அரசு / NGO பகுப்பாய்வு', administration: 'நிர்வாகம்',
    activeRegion: 'செயலில் உள்ள பகுதி', liveDecisionSupport: 'நேரடி முடிவு ஆதரவு', preferences: 'விருப்பங்கள்', signOut: 'வெளியேறு', sriLanka: 'இலங்கை',
    searchPlaceholder: 'வயல், பணி, பயிர் தேடுங்கள்…', search: 'தேடு', noSearchResults: 'பொருந்தும் பண்ணைகள், திட்டங்கள், பணிகள் அல்லது பக்கங்கள் இல்லை.', pages: 'பக்கங்கள்', farms: 'பண்ணைகள்', cropProjects: 'பயிர் திட்டங்கள்', taskResults: 'பணிகள்',
    language: 'மொழி', english: 'English', sinhala: 'සිංහල', tamil: 'தமிழ்', savingLanguage: 'சேமிக்கிறது…',
    notifications: 'அறிவிப்புகள்', markAllRead: 'அனைத்தையும் படித்ததாக குறி', noNotifications: 'இன்னும் அறிவிப்புகள் இல்லை.', allCaughtUp: 'புதிய அறிவிப்புகள் இல்லை.', scheduled: 'திட்டமிடப்பட்டது', openTasks: 'பணி மையத்தைத் திற',
    farmer: 'விவசாயி',
    title_dashboard:'விவசாயி கட்டளை மையம்', title_overview:'தேசிய நுண்ணறிவு மையம்', title_local:'உள்ளூர் நிலை', title_climate:'காலநிலை & பேரிடர் ஆபத்து மையம்', title_disasterMap:'பேரிடர் வரைபடம்', title_satellite:'செயற்கைக்கோள் நுண்ணறிவு', title_community:'சமூக கண்காணிப்பு', title_ai:'MihiMura AI', title_scan:'பயிர் நல ஸ்கேன்', title_recommendations:'பரிந்துரை வரலாறு', title_expert:'நிபுணர் பரிந்துரை', title_farms:'என் பண்ணைகள்', title_farmMap:'பண்ணை வரைபடம்', title_projects:'சாகுபடி திட்டங்கள்', title_tasks:'பணி & அறிவிப்பு மையம்', title_diary:'வயல் பதிவேடு', title_expenses:'செலவுகள்', title_harvest:'அறுவடை & பருவ மதிப்பாய்வு', title_marketplace:'சரிபார்க்கப்பட்ட சந்தை', title_suppliers:'சரிபார்க்கப்பட்ட விநியோகஸ்தர்கள்', title_compare:'பொருள் ஒப்பீடு', title_cart:'கூடை & உறுதிப்படுத்தல்', title_orders:'ஆர்டர்கள் & விநியோகம்', title_reports:'அறிக்கைகள் & SDG தாக்கம்', title_settings:'சுயவிவரம், தனியுரிமை & அணுகல்', title_agronomist:'வேளாண் நிபுணர் கன்சோல்', title_cooperative:'கூட்டுறவு / விநியோகஸ்தர் போர்டல்', title_government:'அரசு / NGO பகுப்பாய்வு', title_admin:'நிர்வாகம் & தரவு செயல்பாடுகள்',
  },
};

const LanguageContext = createContext<LanguageContextValue | null>(null);
const STORAGE_KEY = 'mihimura_app_language';
const valid = (value: unknown): value is AppLanguage => value === 'English' || value === 'Sinhala' || value === 'Tamil';

export function LanguageProvider({ children }: { children: ReactNode }) {
  const { profile, refreshProfile } = useAuth();
  const [language, setLocalLanguage] = useState<AppLanguage>(() => {
    const saved = localStorage.getItem(STORAGE_KEY);
    return valid(saved) ? saved : 'English';
  });
  const [changing, setChanging] = useState(false);

  useEffect(() => {
    if (valid(profile?.language) && profile.language !== language) {
      setLocalLanguage(profile.language);
      localStorage.setItem(STORAGE_KEY, profile.language);
    }
  }, [profile?.language]);

  useEffect(() => {
    document.documentElement.lang = language === 'Sinhala' ? 'si' : language === 'Tamil' ? 'ta' : 'en';
    document.documentElement.dataset.language = language.toLowerCase();
  }, [language]);

  const setLanguage = async (next: AppLanguage) => {
    if (next === language) return;
    const previous = language;
    setLocalLanguage(next);
    localStorage.setItem(STORAGE_KEY, next);
    setChanging(true);
    try {
      await platformApi.saveProfile({ language: next });
      await refreshProfile();
    } catch {
      // The local language still works in demo/offline mode.
    } finally {
      setChanging(false);
    }
    if (!valid(next)) setLocalLanguage(previous);
  };

  const value = useMemo<LanguageContextValue>(() => ({
    language,
    locale: language === 'Sinhala' ? 'si-LK' : language === 'Tamil' ? 'ta-LK' : 'en-LK',
    shortCode: language === 'Sinhala' ? 'සිං' : language === 'Tamil' ? 'த' : 'EN',
    changing,
    setLanguage,
    t: (key: string) => translations[language][key] || translations.English[key] || key,
  }), [language, changing]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage() {
  const ctx = useContext(LanguageContext);
  if (!ctx) throw new Error('useLanguage must be used inside LanguageProvider');
  return ctx;
}
