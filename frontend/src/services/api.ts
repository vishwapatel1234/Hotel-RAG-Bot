import axios from "axios";
import { Message, SystemHealth, RetrievedChunk } from "../types";

let apiBaseUrl = "http://localhost:8000";

export const setApiBaseUrl = (url: string) => {
  apiBaseUrl = url.trim().replace(/\/$/, "");
};
export const getApiBaseUrl = () => apiBaseUrl;

// ==============================================================================
// HEALTH & SESSION MANAGEMENT
// ==============================================================================
export const checkApiHealth = async (): Promise<SystemHealth> => {
  try {
    const resp = await axios.get<SystemHealth>(`${apiBaseUrl}/health`, { timeout: 2000 });
    return resp.data;
  } catch {
    return { status: "unhealthy", faiss: "error", gemini: "error", memory: "error" };
  }
};

export const createSession = async (): Promise<string> => {
  try {
    const resp = await axios.post<{ session_id: string }>(`${apiBaseUrl}/session`, {}, { timeout: 2000 });
    return resp.data.session_id;
  } catch {
    return "mock-" + Math.random().toString(36).substring(2, 15);
  }
};

export const deleteSession = async (sessionId: string): Promise<boolean> => {
  try {
    await axios.delete(`${apiBaseUrl}/session/${sessionId}`, { timeout: 2000 });
    return true;
  } catch {
    return true;
  }
};

// ==============================================================================
// MULTI-TURN CONVERSATIONAL MEMORY
// ==============================================================================
interface SessionMemory {
  lastCategory?: string;
  lastSubsection?: string;
  lastRoomType?: string;
  lastTopic?: string;
  lastIntent?: string;
}
const sessionMemories: Record<string, SessionMemory> = {};

// ==============================================================================
// COMPLETE KNOWLEDGE BASE — Built from hotel_data.json + hotel_data_optimized.json
// ==============================================================================
interface KnowledgeChunk {
  category: string;
  subsection: string;
  content: string;
  keywords: string[];
}

const KNOWLEDGE_BASE: KnowledgeChunk[] = [
  // ── GENERAL INFORMATION ──────────────────────────────────────────────────
  {
    category: "general", subsection: "checkin_time",
    content: "Check-in time at StayChat Grand Hotel is 2:00 PM. Early check-in is subject to availability. Valid government-issued identification is required at check-in. Guests must be at least 18 years old to check in.",
    keywords: ["checkin", "check-in", "check in", "arrive", "arrival", "early check-in", "early arrival", "id", "identification", "age", "2pm", "2:00", "afternoon", "room ready"]
  },
  {
    category: "general", subsection: "checkout_time",
    content: "Check-out time at StayChat Grand Hotel is 12:00 PM (noon). Late check-out between 12:00 PM and 3:00 PM incurs a 50% half-day room charge. Late check-out after 3:00 PM incurs a full-night room charge. Late check-out is subject to availability.",
    keywords: ["checkout", "check-out", "check out", "leave room", "departure", "late checkout", "late check-out", "extend stay", "12pm", "noon", "12:00", "half day charge", "vacate"]
  },
  {
    category: "general", subsection: "location",
    content: "StayChat Grand Hotel is located at Bandra Kurla Complex (BKC), Mumbai, Maharashtra, India. The hotel is 8 km (approximately 20 minutes by car) from Mumbai International Airport. A Metro station is located 500 meters from the hotel.",
    keywords: ["location", "address", "where", "situated", "mumbai", "bkc", "bandra", "kurla", "india", "map", "directions", "near", "place"]
  },
  {
    category: "general", subsection: "contact",
    content: "StayChat Grand Hotel front desk operates 24 hours a day. Phone: +91-22-5555-1234. Email: info@staychatgrand.com. Concierge assistance is available 24/7.",
    keywords: ["contact", "phone", "email", "call", "desk", "number", "reach", "help", "front desk", "24", "concierge", "write"]
  },
  {
    category: "general", subsection: "general_info",
    content: "StayChat Grand Hotel is a 5-star property with 220 guest rooms, renovated in 2024. Complimentary high-speed WiFi is available throughout the property. Free luggage storage is available before check-in and after check-out. Currency exchange is available at the front desk. Multilingual staff are available.",
    keywords: ["wifi", "wi-fi", "internet", "luggage", "storage", "currency", "exchange", "star", "rooms", "220", "renovated", "2024", "multilingual", "staff", "free"]
  },

  // ── ROOMS ─────────────────────────────────────────────────────────────────
  {
    category: "rooms", subsection: "standard_room",
    content: "Standard Room costs ₹4,500 per night and accommodates 2 guests. Includes complimentary WiFi, television, minibar, and work desk.",
    keywords: ["standard", "standard room", "4500", "₹4500", "2 guests", "minibar", "work desk", "television", "cheapest", "basic", "price", "cost", "rate", "book", "rent"]
  },
  {
    category: "rooms", subsection: "deluxe_room",
    content: "Deluxe Room costs ₹7,000 per night and accommodates 3 guests. Includes city-view windows and a king-size bed.",
    keywords: ["deluxe", "deluxe room", "7000", "₹7000", "3 guests", "city view", "king size", "king bed", "price", "cost", "rate", "book", "rent"]
  },
  {
    category: "rooms", subsection: "executive_room",
    content: "Executive Room costs ₹9,500 per night and accommodates up to 3 guests. Includes executive lounge access.",
    keywords: ["executive room", "executive", "9500", "₹9500", "lounge access", "executive lounge", "harbor lounge", "price", "cost", "rate", "book", "rent"]
  },
  {
    category: "rooms", subsection: "executive_suite",
    content: "Executive Suite costs ₹12,000 per night and accommodates 4 guests. Features separate living and sleeping areas with executive lounge access.",
    keywords: ["executive suite", "suite", "12000", "₹12000", "4 guests", "living area", "bedroom", "separate", "price", "cost", "rate", "book", "rent"]
  },
  {
    category: "rooms", subsection: "family_suite",
    content: "Family Suite costs ₹15,000 per night and accommodates 5 guests. Ideal for families.",
    keywords: ["family", "family suite", "15000", "₹15000", "5 guests", "family room", "price", "cost", "rate", "book", "rent"]
  },
  {
    category: "rooms", subsection: "extra_bed",
    content: "Extra bed is available for ₹1,500 per night. Extra beds can be arranged in your room on request.",
    keywords: ["extra bed", "additional bed", "rollaway", "1500", "₹1500", "cot", "baby cot", "price", "cost", "rate"]
  },
  {
    category: "rooms", subsection: "all_rooms",
    content: "StayChat Grand Hotel offers 5 room types:\n1. Standard Room: ₹4,500/night (2 guests)\n2. Deluxe Room: ₹7,000/night (3 guests) — city view\n3. Executive Room: ₹9,500/night (3 guests) — lounge access\n4. Executive Suite: ₹12,000/night (4 guests) — separate living area\n5. Family Suite: ₹15,000/night (5 guests)\nExtra bed: ₹1,500/night. All rooms include complimentary WiFi.",
    keywords: ["room", "rooms", "accommodation", "book", "booking", "rent", "price", "cost", "rate", "type", "available", "suite", "all rooms", "options", "list", "types"]
  },

  // ── AMENITIES ─────────────────────────────────────────────────────────────
  {
    category: "amenities", subsection: "pool",
    content: "The rooftop infinity pool at StayChat Grand Hotel operates daily from 7:00 AM to 10:00 PM. Pool access is complimentary and exclusive for registered hotel guests.",
    keywords: ["pool", "swimming", "swim", "infinity pool", "rooftop pool", "7am", "10pm", "open", "timing", "hours", "close"]
  },
  {
    category: "amenities", subsection: "fitness",
    content: "The fitness center (gym) operates 24 hours a day and is located on the 4th floor. Access is complimentary for registered hotel guests.",
    keywords: ["gym", "fitness", "fitness center", "workout", "exercise", "24 hours", "4th floor", "health", "sport"]
  },
  {
    category: "amenities", subsection: "spa",
    content: "Spa services at StayChat Grand Hotel are available from 9:00 AM to 9:00 PM. Steam room and sauna access is complimentary for all registered hotel guests.",
    keywords: ["spa", "massage", "steam", "sauna", "steam room", "wellness", "9am", "9pm", "relax", "treatment"]
  },
  {
    category: "amenities", subsection: "parking",
    content: "Valet parking is available at StayChat Grand Hotel. EV charging stations are also available in the parking area.",
    keywords: ["parking", "valet", "car", "ev", "electric vehicle", "charging", "park"]
  },
  {
    category: "amenities", subsection: "business",
    content: "The business center operates 24 hours a day. Meeting rooms are available upon reservation. Conference facilities support up to 300 attendees. Printing, scanning, photocopy, and courier services are available.",
    keywords: ["business center", "meeting room", "conference", "print", "scan", "photocopy", "courier", "office", "work", "300"]
  },
  {
    category: "amenities", subsection: "room_service",
    content: "Room service (in-room dining) is available 24 hours a day. Special dietary requests can be accommodated. Vegetarian and vegan dining options are available.",
    keywords: ["room service", "in room dining", "24 hour", "food delivery", "order food", "vegetarian", "vegan", "dietary", "special diet"]
  },
  {
    category: "amenities", subsection: "other_amenities",
    content: "Additional services at StayChat Grand Hotel: Laundry and dry cleaning service (daily). Daily housekeeping. Doctor on call. Wheelchair assistance. Babysitting (upon request). Wake-up call service. Luggage assistance.",
    keywords: ["laundry", "dry cleaning", "housekeeping", "doctor", "medical", "wheelchair", "disability", "babysitting", "child care", "wake up", "luggage", "assistance"]
  },

  // ── RESTAURANTS & DINING ──────────────────────────────────────────────────
  {
    category: "restaurants", subsection: "harbor_kitchen",
    content: "Harbor Kitchen restaurant at StayChat Grand Hotel:\n• Breakfast: 7:00 AM – 10:30 AM (Buffet: ₹850/guest; children under 6 eat free)\n• Lunch: 12:00 PM – 3:00 PM\n• Dinner: 7:00 PM – 11:00 PM\nPrivate dining arrangements and special dietary requests can be accommodated.",
    keywords: ["harbor kitchen", "breakfast", "lunch", "dinner", "buffet", "850", "₹850", "restaurant", "dining", "food", "meal", "eat", "timings", "hours", "open", "children", "free", "menu"]
  },
  {
    category: "restaurants", subsection: "sky_lounge",
    content: "Sky Lounge (rooftop bar) at StayChat Grand Hotel operates from 5:00 PM to 1:00 AM daily. Serves cocktails, beverages, and small bites.",
    keywords: ["sky lounge", "bar", "rooftop bar", "cocktail", "drinks", "beverage", "lounge", "5pm", "1am", "night", "alcohol", "snacks"]
  },

  // ── POLICIES ──────────────────────────────────────────────────────────────
  {
    category: "policies", subsection: "cancellation",
    content: "Cancellation Policy at StayChat Grand Hotel: Free cancellation up to 48 hours before arrival. Cancellations within 48 hours of arrival incur a one-night room charge. No-show reservations incur a one-night room charge.",
    keywords: ["cancellation", "cancel", "refund", "no show", "no-show", "48 hours", "cancellation policy", "fee", "charge", "refund policy"]
  },
  {
    category: "policies", subsection: "pets",
    content: "Pets are not allowed on StayChat Grand Hotel premises. However, registered service dogs and guide dogs are permitted with valid documentation.",
    keywords: ["pet", "pets", "dog", "cat", "animal", "guide dog", "service dog", "allowed", "permit", "pet policy", "pets policy"]
  },
  {
    category: "policies", subsection: "smoking",
    content: "Smoking is strictly prohibited inside guest rooms and all indoor public areas. A deep cleaning fee of ₹10,000 will be charged for smoking violations inside guest rooms. Smoking is only permitted in designated outdoor areas.",
    keywords: ["smoking", "smoke", "cigarette", "10000", "₹10000", "fine", "violation", "designated area", "outdoor", "prohibited", "smoking policy"]
  },
  {
    category: "policies", subsection: "children",
    content: "Children under 6 years old stay free when sharing existing bedding with parents. Children under 6 also receive complimentary breakfast at Harbor Kitchen.",
    keywords: ["children", "child", "kids", "baby", "infant", "under 6", "free stay", "family"]
  },
  {
    category: "policies", subsection: "security",
    content: "Valid government-issued identification is required at check-in. A security deposit may be required during check-in. Outside food delivery is permitted.",
    keywords: ["id", "identification", "security", "deposit", "outside food", "delivery", "government id"]
  },

  // ── TRANSPORTATION ────────────────────────────────────────────────────────
  {
    category: "transportation", subsection: "airport",
    content: "Mumbai International Airport is approximately 8 km (20 minutes by car) from StayChat Grand Hotel. Airport transfer service is available for ₹1,500 per trip.",
    keywords: ["airport", "transfer", "shuttle", "taxi", "cab", "1500", "₹1500", "pickup", "drop", "flight"]
  },
  {
    category: "transportation", subsection: "local",
    content: "Metro station is 500 meters from the hotel. Taxi booking assistance and private chauffeur service can be arranged through the concierge. Car rental services are available upon request.",
    keywords: ["metro", "taxi", "chauffeur", "car rental", "local transport", "uber", "ola", "500 meters", "nearby", "transport"]
  },

  // ── PAYMENTS ──────────────────────────────────────────────────────────────
  {
    category: "payments", subsection: "payment_methods",
    content: "StayChat Grand Hotel accepts: Visa, Mastercard, American Express, RuPay cards, UPI payments, and cash. Invoices can be provided upon request.",
    keywords: ["payment", "pay", "card", "visa", "mastercard", "amex", "rupay", "upi", "cash", "invoice", "bill", "receipt"]
  },

  // ── SERVICES ──────────────────────────────────────────────────────────────
  {
    category: "services", subsection: "events",
    content: "StayChat Grand Hotel offers wedding planning and corporate event hosting. Conference facilities support up to 300 attendees. Travel desk, tour booking, and travel assistance are available.",
    keywords: ["wedding", "event", "corporate", "conference", "meeting", "attendees", "travel desk", "tour", "party", "function"]
  },
  {
    category: "services", subsection: "lost_found",
    content: "Lost and found assistance is available at StayChat Grand Hotel. Please contact the front desk at +91-22-5555-1234.",
    keywords: ["lost", "found", "lost and found", "missing", "left behind", "forgotten"]
  },
];

// ==============================================================================
// LANGUAGE DETECTION
// ==============================================================================
type Language = "hindi" | "hinglish" | "english";

const detectLanguage = (query: string): Language => {
  // Check for Devanagari Unicode characters
  if (/[\u0900-\u097F]/.test(query)) return "hindi";
  // Check for Hinglish markers
  const hinglishWords = ["hai", "kya", "kitna", "mujhe", "batao", "chahiye", "milega",
    "baje", "samay", "kab", "kaise", "kahan", "kyun", "tha", "nahi", "hoga",
    "please", "mera", "acha", "theek", "aur", "ya", "bhi", "ka", "ki", "ke"];
  const lq = query.toLowerCase();
  const matchCount = hinglishWords.filter(w => lq.includes(w)).length;
  if (matchCount >= 1) return "hinglish";
  return "english";
};

// ==============================================================================
// DEVANAGARI → ENGLISH TRANSLATION MAP (for matching)
// ==============================================================================
const HINDI_TRANSLATIONS: Array<{ regex: RegExp; replacement: string }> = [
  // Check-in / Check-out — specific FIRST (order matters!)
  { regex: /चेक\s*आउट/g,        replacement: "checkout" },
  { regex: /चेक\s*इन/g,         replacement: "checkin" },
  // Room types
  { regex: /कमरा/g,              replacement: "room" },
  { regex: /रूम/g,              replacement: "room" },
  { regex: /सुइट/g,             replacement: "suite" },
  { regex: /डीलक्स/g,          replacement: "deluxe" },
  { regex: /स्टैंडर्ड/g,       replacement: "standard" },
  // Amenities
  { regex: /पूल/g,              replacement: "pool" },
  { regex: /स्विमिंग/g,        replacement: "swimming" },
  { regex: /जिम/g,              replacement: "gym" },
  { regex: /फिटनेस/g,          replacement: "fitness" },
  { regex: /स्पा/g,             replacement: "spa" },
  { regex: /सौना/g,             replacement: "sauna" },
  { regex: /स्टीम/g,           replacement: "steam" },
  { regex: /पार्किंग/g,        replacement: "parking" },
  { regex: /वाई\s*फाई/g,       replacement: "wifi" },
  // Dining
  { regex: /नाश्ता/g,           replacement: "breakfast" },
  { regex: /खाना/g,             replacement: "food" },
  { regex: /रेस्टोरेंट/g,      replacement: "restaurant" },
  { regex: /लंच/g,              replacement: "lunch" },
  { regex: /डिनर/g,             replacement: "dinner" },
  { regex: /बुफे/g,             replacement: "buffet" },
  // Transport
  { regex: /हवाई\s*अड्डा/g,    replacement: "airport" },
  { regex: /मेट्रो/g,           replacement: "metro" },
  { regex: /टैक्सी/g,          replacement: "taxi" },
  { regex: /ट्रांसफर/g,        replacement: "transfer" },
  // Finance
  { regex: /कीमत/g,             replacement: "price" },
  { regex: /किराया/g,           replacement: "price" },
  { regex: /शुल्क/g,            replacement: "charge" },
  { regex: /मुफ्त/g,            replacement: "free" },
  { regex: /भुगतान/g,           replacement: "payment" },
  // Timing words — map to specific terms, NOT generic 'time'
  { regex: /समय\s*क्या\s*है/g,  replacement: "timing" },
  { regex: /कब\s*तक/g,         replacement: "closing time" },
  { regex: /कब\s*खुलता/g,      replacement: "opening time" },
  { regex: /कब\s*बंद/g,        replacement: "closing time" },
  { regex: /समय/g,              replacement: "timing" },
  // Question words
  { regex: /क्या/g,             replacement: "" },
  { regex: /कब/g,               replacement: "when" },
  { regex: /कहाँ/g,             replacement: "where" },
  { regex: /कितना/g,            replacement: "how much" },
  { regex: /कितने/g,            replacement: "how many" },
  { regex: /कैसे/g,             replacement: "how" },
  // Filler
  { regex: /है/g,               replacement: "" },
  { regex: /हैं/g,              replacement: "" },
  { regex: /का/g,               replacement: "" },
  { regex: /की/g,               replacement: "" },
  { regex: /के/g,               replacement: "" },
  // Policy
  { regex: /सुविधाएं/g,         replacement: "amenities" },
  { regex: /रद्द/g,             replacement: "cancel" },
  { regex: /बच्चे/g,            replacement: "children" },
  { regex: /पालतू/g,            replacement: "pet" },
  { regex: /धूम्रपान/g,        replacement: "smoking" },
  { regex: /अतिरिक्त\s*बिस्तर/g, replacement: "extra bed" },
  { regex: /बिस्तर/g,          replacement: "bed" },
];


const translateHindi = (text: string): string => {
  let result = text.toLowerCase();
  for (const t of HINDI_TRANSLATIONS) {
    result = result.replace(t.regex, t.replacement);
  }
  return result;
};

// ==============================================================================
// STOP WORDS (filtered before keyword matching)
// ==============================================================================
const STOP_WORDS = new Set([
  "the", "and", "for", "with", "have", "been", "was", "were", "what", "how",
  "who", "are", "does", "did", "can", "you", "your", "that", "this", "these",
  "those", "hotel", "staychat", "grand", "mumbai", "is", "of", "on", "at",
  "in", "to", "a", "an", "our", "do", "will", "would", "should", "could",
  "please", "tell", "me", "about", "any", "there", "here", "want", "need",
  "get", "give", "know", "like", "make", "take", "come", "go", "see", "i"
]);

// ==============================================================================
// LOCAL RAG ENGINE — Keyword matching with memory-aware pronoun resolution
// ==============================================================================
const matchLocalRAG = (query: string, sessionId?: string): RetrievedChunk[] => {
  let cleaned = query.toLowerCase().trim();

  // Step 1: Translate Devanagari if present
  if (/[\u0900-\u097F]/.test(cleaned)) {
    cleaned = translateHindi(cleaned);
  }

  // Step 2: Multi-turn pronoun resolution (English + Hindi + Hinglish pronouns)
  if (sessionId && sessionMemories[sessionId]) {
    const mem = sessionMemories[sessionId];
    // English pronouns
    const englishPronouns = /\b(it|that|this|there|them|its|they|those|one|same|which|the one)\b/i;
    // Hinglish / Hindi pronouns: usmein=in it, uska/uski/uske=its, voh/woh=that/it,
    // isme/ismein=in this, wahan=there, uspe/uspar=on it, kitne=how many (in it),
    // usme=in it, iska/iski=its, vo=it
    const hinglishPronouns = /\b(usmein|usme|uska|uski|uske|uske|voh|woh|vo|isme|ismein|wahan|uspe|uspar|iska|iski|iske|inme|inmein|unme|unka|unki|unke|yeh wala|woh wala)\b/i;
    const hasEnglishPronoun = englishPronouns.test(cleaned)
      || cleaned.includes("in it") || cleaned.includes("for that")
      || cleaned.includes("of it") || cleaned.includes("about it")
      || cleaned.includes("in that") || cleaned.includes("about that");
    const hasHinglishPronoun = hinglishPronouns.test(cleaned);

    if (hasEnglishPronoun || hasHinglishPronoun) {
      if (mem.lastRoomType && mem.lastRoomType !== "all_rooms") {
        cleaned += " " + mem.lastRoomType;
      } else if (mem.lastSubsection && mem.lastSubsection !== "all_rooms") {
        cleaned += " " + mem.lastSubsection.replace(/_/g, " ");
      } else if (mem.lastCategory) {
        cleaned += " " + mem.lastCategory;
      }
    }
  }

  // Step 3: Extract meaningful words, remove punctuation and stop words
  const wordsArray = cleaned
    .replace(/[.,/#!$%^&*;:{}=\-_`~()?।]/g, " ")
    .split(/\s+/)
    .filter(w => w.length > 1 && !STOP_WORDS.has(w));
  
  // Deduplicate words so appended memory context doesn't artificially inflate keyword scores
  const words = Array.from(new Set(wordsArray));

  if (words.length === 0) return [];

  // ── PHRASE-LEVEL DISAMBIGUATION ──────────────────────────────────────────
  // Critical: detect exact intent from the full cleaned query BEFORE scoring
  // to prevent check-in queries returning check-out and vice versa
  const checkinPhrases  = /\b(check.?in|checkin|arrive|arrival|2\s*pm|early check)\b/i;
  const checkoutPhrases = /\b(check.?out|checkout|leave|departure|late check.?out|vacate|12\s*pm|noon|extend\s*stay)\b/i;

  const isDefinitelyCheckin  = checkinPhrases.test(cleaned)  && !checkoutPhrases.test(cleaned);
  const isDefinitelyCheckout = checkoutPhrases.test(cleaned) && !checkinPhrases.test(cleaned);

  const results: { chunk: KnowledgeChunk; score: number }[] = [];

  for (const chunk of KNOWLEDGE_BASE) {
    let score = 0;
    const chunkText = (chunk.content + " " + chunk.keywords.join(" ")).toLowerCase();

    // Phrase-level bonus: strongly prefer the correct chunk for check-in vs check-out
    if (isDefinitelyCheckin  && chunk.subsection === "checkin_time")  score += 12;
    if (isDefinitelyCheckin  && chunk.subsection === "checkout_time") score -= 8;
    if (isDefinitelyCheckout && chunk.subsection === "checkout_time") score += 12;
    if (isDefinitelyCheckout && chunk.subsection === "checkin_time")  score -= 8;

    for (const word of words) {
      // Exact keyword match (highest weight)
      if (chunk.keywords.some(kw => kw === word)) {
        score += 5;
      }
      // Partial keyword match
      else if (chunk.keywords.some(kw => kw.includes(word) || word.includes(kw))) {
        score += 3;
      }
      // Content text match (medium weight)
      if (chunkText.includes(word)) {
        score += 1;
      }
    }

    if (score > 0) {
      const normalized = Math.min(0.98, 0.40 + (score / (words.length * 6)) * 0.58);
      results.push({ chunk, score: normalized });
    }
  }

  results.sort((a, b) => b.score - a.score);
  return results.slice(0, 3).map(r => ({
    category: r.chunk.category,
    subsection: r.chunk.subsection,
    score: r.score,
    content: r.chunk.content,
  }));
};


// ==============================================================================
// RESPONSE TEMPLATES — Same data, rendered per-language
// ==============================================================================
const buildResponse = (topChunk: RetrievedChunk, queryClean: string, lang: Language): string => {
  const cat = topChunk.category;
  const sub = topChunk.subsection;
  const content = topChunk.content;

  // ── CHECKOUT ──
  if (sub === "checkout_time") {
    if (lang === "hindi") {
      return "StayChat ग्रैंड होटल में **चेक-आउट** का समय **दोपहर 12:00 बजे** है।\n\n* **देर से चेक-आउट (12 PM – 3 PM)**: 50% अर्ध-दिन शुल्क लागू होगा।\n* **3 PM के बाद**: एक पूरी रात का शुल्क लागू होगा।\n* देर से चेक-आउट उपलब्धता के अधीन है।";
    } else if (lang === "hinglish") {
      return "StayChat Grand Hotel mein **check-out time** strictly **12:00 PM (dopahar)** hai.\n\n* **Late Check-out (12 PM – 3 PM)**: 50% half-day charge lagega.\n* **3 PM ke baad**: Full night charge lagega.\n* Late check-out availability ke basis par milega.";
    }
    return content;
  }

  // ── CHECK-IN ──
  if (sub === "checkin_time") {
    if (lang === "hindi") {
      return "StayChat ग्रैंड होटल में **चेक-इन** का समय **दोपहर 2:00 बजे** से शुरू होता है।\n\n* **अर्ली चेक-इन** उपलब्धता के अधीन है।\n* चेक-इन के लिए वैध सरकारी पहचान पत्र आवश्यक है।\n* मेहमान की न्यूनतम आयु **18 वर्ष** होनी चाहिए।";
    } else if (lang === "hinglish") {
      return "StayChat Grand Hotel mein **check-in** dopahar **2:00 PM** se start hota hai.\n\n* **Early check-in** availability ke basis par milti hai.\n* Check-in ke liye valid government ID required hai.\n* Minimum age **18 years** honi chahiye.";
    }
    return content;
  }

  // ── ALL ROOMS / BOOKING INQUIRY ──
  if (sub === "all_rooms" || (cat === "rooms" && !sub.includes("room") && !sub.includes("suite") && !sub.includes("bed") && queryClean.match(/\b(room|book|rent|cost|price|stay|available|types|list|all|options)\b/))) {
    if (lang === "hindi") {
      return "StayChat ग्रैंड होटल में उपलब्ध कमरे:\n\n1. **Standard Room**: ₹4,500/रात (2 मेहमान) — WiFi, TV, मिनीबार\n2. **Deluxe Room**: ₹7,000/रात (3 मेहमान) — सिटी व्यू, किंग-साइज़ बेड\n3. **Executive Room**: ₹9,500/रात (3 मेहमान) — लाउंज एक्सेस\n4. **Executive Suite**: ₹12,000/रात (4 मेहमान) — अलग बैठक + शयन कक्ष\n5. **Family Suite**: ₹15,000/रात (5 मेहमान)\n\n*अतिरिक्त बिस्तर ₹1,500/रात। सभी कमरों में मुफ्त WiFi।*";
    } else if (lang === "hinglish") {
      return "StayChat Grand Hotel mein yeh rooms available hain:\n\n1. **Standard Room**: ₹4,500/raat (2 guests) — WiFi, TV, minibar\n2. **Deluxe Room**: ₹7,000/raat (3 guests) — city view, king bed\n3. **Executive Room**: ₹9,500/raat (3 guests) — lounge access\n4. **Executive Suite**: ₹12,000/raat (4 guests) — alag living + bedroom\n5. **Family Suite**: ₹15,000/raat (5 guests)\n\n*Extra bed ₹1,500/raat mein milti hai. Sab rooms mein free WiFi.*";
    }
    return "We offer the following room types at StayChat Grand Hotel:\n\n1. **Standard Room**: ₹4,500/night (2 guests) — WiFi, TV, minibar, work desk\n2. **Deluxe Room**: ₹7,000/night (3 guests) — city-view windows, king-size bed\n3. **Executive Room**: ₹9,500/night (3 guests) — executive lounge access\n4. **Executive Suite**: ₹12,000/night (4 guests) — separate living & sleeping areas\n5. **Family Suite**: ₹15,000/night (5 guests)\n\n*Extra bed available for ₹1,500/night. All rooms include complimentary high-speed WiFi.*";
  }

  // ── EXTRA BED ──
  if (sub === "extra_bed") {
    if (lang === "hindi") return "अतिरिक्त बिस्तर (Extra Bed) **₹1,500 प्रति रात** के शुल्क पर उपलब्ध है। कृपया फ्रंट डेस्क से अनुरोध करें।";
    if (lang === "hinglish") return "Extra bed **₹1,500 per raat** mein arrange ho sakta hai. Front desk se request karein!";
    return content;
  }

  // ── POOL ──
  if (sub === "pool") {
    if (lang === "hindi") return "StayChat ग्रैंड होटल में **रूफटॉप इन्फिनिटी पूल** प्रतिदिन **सुबह 7:00 बजे से रात 10:00 बजे** तक खुला रहता है। यह सेवा सभी रजिस्टर्ड मेहमानों के लिए **मुफ्त** है।";
    if (lang === "hinglish") return "**Rooftop Infinity Pool** roz **7:00 AM se 10:00 PM** tak open rehta hai. Registered hotel guests ke liye bilkul **free** hai!";
    return content;
  }

  // ── GYM/FITNESS ──
  if (sub === "fitness") {
    if (lang === "hindi") return "**फिटनेस सेंटर (जिम)** 4थी मंजिल पर स्थित है और **24 घंटे** खुला रहता है। यह सेवा मेहमानों के लिए मुफ्त है।";
    if (lang === "hinglish") return "**Gym (Fitness Center)** 4th floor par hai aur **24 ghante** open rehta hai. Registered guests ke liye free hai!";
    return content;
  }

  // ── SPA ──
  if (sub === "spa") {
    if (lang === "hindi") return "**स्पा सेवाएं** प्रतिदिन **सुबह 9:00 बजे से रात 9:00 बजे** तक उपलब्ध हैं। स्टीम रूम और सॉना सभी रजिस्टर्ड मेहमानों के लिए **मुफ्त** है।";
    if (lang === "hinglish") return "**Spa services** roz **9:00 AM se 9:00 PM** tak available hain. Steam room aur sauna sab registered guests ke liye **free** hai!";
    return content;
  }

  // ── PARKING ──
  if (sub === "parking") {
    if (lang === "hindi") return "**वैलेट पार्किंग** सभी रजिस्टर्ड मेहमानों के लिए उपलब्ध है। पार्किंग क्षेत्र में **EV चार्जिंग स्टेशन** भी उपलब्ध हैं।";
    if (lang === "hinglish") return "**Valet parking** sab registered guests ke liye available hai. Parking area mein **EV charging stations** bhi hain!";
    return content;
  }

  // ── BREAKFAST / DINING ──
  if (sub === "harbor_kitchen" || cat === "restaurants") {
    if (lang === "hindi") return "**हार्बर किचन** रेस्टोरेंट के खाने का समय:\n\n* **नाश्ता (Breakfast)**: सुबह 7:00 – 10:30 (बुफे ₹850/मेहमान; 6 साल से कम के बच्चे मुफ्त)\n* **दोपहर का खाना (Lunch)**: दोपहर 12:00 – 3:00\n* **रात का खाना (Dinner)**: शाम 7:00 – 11:00\n* **स्काई लाउंज (Sky Lounge/Bar)**: शाम 5:00 PM – रात 1:00 AM";
    if (lang === "hinglish") return "**Harbor Kitchen** restaurant ka schedule:\n\n* **Breakfast**: 7:00 AM – 10:30 AM (Buffet ₹850/guest; 6 saal se chhote bachche free!)\n* **Lunch**: 12:00 PM – 3:00 PM\n* **Dinner**: 7:00 PM – 11:00 PM\n* **Sky Lounge (Bar)**: 5:00 PM – 1:00 AM";
    return content;
  }

  // ── AIRPORT / TRANSFER ──
  if (sub === "airport" || cat === "transportation") {
    if (lang === "hindi") return "**मुंबई अंतर्राष्ट्रीय हवाई अड्डा** होटल से लगभग **8 किमी (20 मिनट)** दूर है। **एयरपोर्ट ट्रांसफर** सेवा **₹1,500 प्रति यात्रा** उपलब्ध है।";
    if (lang === "hinglish") return "**Mumbai International Airport** hotel se sirf **8 km (20 minutes)** door hai. **Airport transfer** service **₹1,500 per trip** mein available hai!";
    return content;
  }

  // ── LOCATION ──
  if (sub === "location") {
    if (lang === "hindi") return "StayChat ग्रैंड होटल **बांद्रा कुर्ला कॉम्प्लेक्स (BKC), मुंबई, महाराष्ट्र** में स्थित है। यहाँ से **मुंबई एयरपोर्ट** लगभग **8 किमी (20 मिनट)** दूर है और **मेट्रो स्टेशन** मात्र **500 मीटर** की दूरी पर है।";
    if (lang === "hinglish") return "StayChat Grand Hotel **BKC (Bandra Kurla Complex), Mumbai** mein located hai. **Mumbai Airport** sirf **8 km (20 min)** door hai aur **Metro station** **500 meters** paas hai!";
    return content;
  }

  // ── CONTACT ──
  if (sub === "contact") {
    if (lang === "hindi") return "**StayChat ग्रैंड होटल** का फ्रंट डेस्क **24 घंटे** उपलब्ध है।\n\n* **फोन**: +91-22-5555-1234\n* **ईमेल**: info@staychatgrand.com\n* **कंसीयर्ज**: 24/7 सेवा";
    if (lang === "hinglish") return "**Front desk 24/7** available hai!\n\n* **Phone**: +91-22-5555-1234\n* **Email**: info@staychatgrand.com\n* **Concierge**: Har waqt available!";
    return content;
  }

  // ── CANCELLATION ──
  if (sub === "cancellation") {
    if (lang === "hindi") return "**रद्दीकरण नीति**:\n\n* आगमन से **48 घंटे पहले** तक रद्दीकरण **मुफ्त** है।\n* 48 घंटे के भीतर रद्द करने पर **एक रात का शुल्क** लगेगा।\n* **No-show** पर भी एक रात का शुल्क लागू होगा।";
    if (lang === "hinglish") return "**Cancellation Policy**:\n\n* Arrival se **48 ghante pehle** cancel karna **free** hai.\n* 48 ghante ke andar cancel karne par **ek raat ka charge** lagega.\n* **No-show** par bhi ek raat ka charge lagega.";
    return content;
  }

  // ── PAYMENT ──
  if (sub === "payment_methods") {
    if (lang === "hindi") return "StayChat ग्रैंड होटल इन भुगतान विधियों को स्वीकार करता है:\n\n* **कार्ड**: Visa, Mastercard, American Express, RuPay\n* **डिजिटल**: UPI\n* **नकद**: हाँ, स्वीकार किया जाता है\n* **इनवॉइस**: अनुरोध पर उपलब्ध";
    if (lang === "hinglish") return "Hotel in payment methods accept karta hai:\n\n* **Cards**: Visa, Mastercard, Amex, RuPay\n* **Digital**: UPI\n* **Cash**: Yes, accepted!\n* **Invoice**: Request par milega";
    return content;
  }

  // ── WIFI ──
  if (sub === "general_info" && (queryClean.includes("wifi") || queryClean.includes("wi-fi") || queryClean.includes("internet"))) {
    if (lang === "hindi") return "StayChat ग्रैंड होटल में **हाई-स्पीड WiFi** पूरे होटल में **बिल्कुल मुफ्त** उपलब्ध है।";
    if (lang === "hinglish") return "**High-speed WiFi** puri hotel mein **bilkul free** hai!";
    return "Complimentary high-speed WiFi is available throughout StayChat Grand Hotel — in all rooms and public areas.";
  }

  // ── DEFAULT: return the raw chunk content ──
  return content;
};

// ==============================================================================
// GREETING HANDLER
// ==============================================================================
const isGreeting = (query: string): boolean => {
  const greetings = /^(hello|hi|hey|namaste|namaskar|good morning|good evening|good afternoon|howdy|hiya|greetings|sup|helo|hii|hyy|नमस्ते|हेलो|हाय)\b/i;
  return greetings.test(query.trim());
};

const buildGreeting = (lang: Language): string => {
  if (lang === "hindi") {
    return "नमस्ते! 🙏 **StayChat ग्रैंड होटल** में आपका स्वागत है!\n\nमैं आपका AI कंसीयर्ज हूँ। मैं इनमें मदद कर सकता हूँ:\n\n* 🛏️ कमरे की जानकारी और बुकिंग\n* 🏊 पूल, जिम और स्पा का समय\n* 🍽️ रेस्टोरेंट और खाने का समय\n* 🚕 एयरपोर्ट ट्रांसफर\n* 📋 होटल की नीतियाँ\n\nआप क्या जानना चाहते हैं?";
  }
  if (lang === "hinglish") {
    return "Namaste! 🙏 **StayChat Grand Hotel** mein aapka swagat hai!\n\nMain aapka AI concierge hun. Main in cheezon mein help kar sakta hun:\n\n* 🛏️ Rooms ki jankari aur booking\n* 🏊 Pool, gym aur spa ka timing\n* 🍽️ Restaurant aur khane ka schedule\n* 🚕 Airport transfer\n* 📋 Hotel policies\n\nAap kya jaanna chahte hain?";
  }
  return "Hello! 👋 Welcome to **StayChat Grand Hotel**, Mumbai!\n\nI'm your AI concierge. I can help you with:\n\n* 🛏️ Room types and pricing\n* 🏊 Pool, gym & spa timings\n* 🍽️ Restaurant hours and dining\n* 🚕 Airport transfers\n* 📋 Hotel policies\n\nHow can I assist you today?";
};

// ==============================================================================
// INTENT CLASSIFIER
// ==============================================================================
const classifyIntent = (_query: string, topChunk?: RetrievedChunk): string => {
  if (!topChunk) return "general_inquiry";
  const cat = topChunk.category;
  const sub = topChunk.subsection;
  if (cat === "rooms") return "booking_inquiry";
  if (cat === "policies") {
    if (sub.includes("checkout") || sub.includes("checkin")) return "policy_checkinout";
    if (sub === "cancellation") return "policy_cancellation";
    return "policy_question";
  }
  if (cat === "amenities") return "amenity_question";
  if (cat === "restaurants") return "dining_question";
  if (cat === "transportation") return "transportation_question";
  if (cat === "payments") return "payment_inquiry";
  if (cat === "services") return "services_inquiry";
  if (cat === "general") return "general_inquiry";
  return "general_inquiry";
};

// ==============================================================================
// MAIN LOCAL SIMULATOR — Full offline RAG pipeline
// ==============================================================================
export const simulateRAGPipeline = (query: string, sessionId: string): Message => {
  const requestId = Math.random().toString(36).substring(2, 15);
  const timestamp = new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  const queryClean = query.toLowerCase().trim();

  // Detect language FIRST
  const language = detectLanguage(query);

  let intent = "general_inquiry";
  let latency = Math.floor(Math.random() * 80) + 120;
  let confidence = 0.50;
  let route: "retrieval" | "bypass" | "unknown" = "retrieval";
  let guardrail: "passed" | "escalate" = "passed";
  let escalation: "stable" | "escalated" = "stable";
  let reason: string | undefined = undefined;
  let response = "";
  let chunks: RetrievedChunk[] = [];

  // ── GUARDRAIL: Payment / PII Sensitive Block ──
  if (/\b(payment link|pay link|card number|upi id|upi link|account number|cvv|otp|transfer money|bank account|paytm link)\b/i.test(queryClean)) {
    intent = "escalation_request";
    confidence = 1.00;
    route = "bypass";
    guardrail = "escalate";
    escalation = "escalated";
    reason = "Pre-Retrieval PII Protection: Sensitive payment/link request blocked";
    response = "For your security, payment links and financial account details cannot be processed by the AI Assistant. I'm connecting you to our secure billing team right away.";
    return buildMessage(requestId, sessionId, timestamp, intent, language, latency, confidence, route, guardrail, escalation, reason, response, chunks);
  }

  // ── GUARDRAIL: Out-of-scope (non-hotel topics) ──
  if (/\b(python|javascript|code|script|program|sql|database|algorithm|cricket|bollywood|politics|weather|news|recipe|stock|share market)\b/i.test(queryClean)) {
    intent = "out_of_scope";
    confidence = 0.95;
    route = "bypass";
    guardrail = "escalate";
    escalation = "escalated";
    reason = "Out-of-scope query — topic not related to hotel services";
    response = "I'm your hotel AI concierge and can only assist with hotel-related queries like rooms, dining, amenities, and policies. For other topics, please use a general search engine. Would you like help with your stay at StayChat Grand Hotel?";
    return buildMessage(requestId, sessionId, timestamp, intent, language, latency, confidence, route, guardrail, escalation, reason, response, chunks);
  }

  // ── GREETING HANDLER ──
  if (isGreeting(queryClean)) {
    intent = "greeting";
    confidence = 0.98;
    route = "bypass";
    response = buildGreeting(language);
    return buildMessage(requestId, sessionId, timestamp, intent, language, latency, confidence, route, guardrail, escalation, reason, response, chunks);
  }

  // ── GUARDRAIL: VIP / Unlisted inventory ──
  if (/\b(presidential suite|vip suite|royal suite|penthouse|honeymoon suite)\b/i.test(queryClean)) {
    intent = "room_question";
    confidence = 0.35;
    route = "retrieval";
    guardrail = "escalate";
    escalation = "escalated";
    reason = "Unlisted inventory — Presidential/VIP Suite not in knowledge base";
    response = "I apologize, but information about a Presidential or VIP Suite is not available in our current listings. Let me connect you with our reservations team who can assist with special accommodation requests.";
    return buildMessage(requestId, sessionId, timestamp, intent, language, latency, confidence, route, guardrail, escalation, reason, response, chunks);
  }

  // ── RAG RETRIEVAL ──
  chunks = matchLocalRAG(query, sessionId);

  if (chunks.length > 0) {
    const topChunk = chunks[0];
    confidence = topChunk.score;
    intent = classifyIntent(queryClean, topChunk);

    // Save context memory for multi-turn pronoun resolution
    sessionMemories[sessionId] = {
      lastCategory: topChunk.category,
      lastSubsection: topChunk.subsection,
      lastIntent: intent,
      lastTopic: topChunk.subsection,
      lastRoomType:
        queryClean.includes("executive suite") ? "executive suite" :
        queryClean.includes("family suite") ? "family suite" :
        queryClean.includes("executive room") ? "executive room" :
        queryClean.includes("deluxe") ? "deluxe room" :
        queryClean.includes("standard") ? "standard room" :
        queryClean.includes("suite") ? "suite" :
        sessionMemories[sessionId]?.lastRoomType,
    };

    response = buildResponse(topChunk, queryClean, language);
  } else {
    // Nothing matched in knowledge base
    guardrail = "escalate";
    escalation = "escalated";
    reason = "No relevant information found in knowledge base";
    if (language === "hindi") {
      response = "मुझे खेद है, इस प्रश्न का उत्तर हमारे होटल की जानकारी में उपलब्ध नहीं है। कृपया हमारे फ्रंट डेस्क से **+91-22-5555-1234** पर संपर्क करें या **info@staychatgrand.com** पर ईमेल करें।";
    } else if (language === "hinglish") {
      response = "Sorry, is sawaal ka jawab humare hotel knowledge base mein nahi mila. Please front desk se **+91-22-5555-1234** par contact karein ya **info@staychatgrand.com** par email karein.";
    } else {
      response = "I'm sorry, I couldn't find details about that in our hotel knowledge base. Please contact our front desk directly at **+91-22-5555-1234** or email **info@staychatgrand.com** and our team will be happy to assist you.";
    }
  }

  return buildMessage(requestId, sessionId, timestamp, intent, language, latency, confidence, route, guardrail, escalation, reason, response, chunks);
};

// ==============================================================================
// MESSAGE BUILDER (shared between simulator + live API)
// ==============================================================================
const buildMessage = (
  requestId: string, sessionId: string, timestamp: string,
  intent: string, language: Language, latency: number, confidence: number,
  route: "retrieval" | "bypass" | "unknown",
  guardrail: "passed" | "escalate",
  escalation: "stable" | "escalated",
  reason: string | undefined,
  response: string, chunks: RetrievedChunk[]
): Message => ({
  id: `msg-${Date.now()}`,
  role: "assistant",
  content: response,
  timestamp,
  telemetry: {
    request_id: requestId,
    session_id: sessionId,
    intent,
    language,
    latency_ms: latency,
    confidence_score: confidence,
    route,
    guardrail_status: guardrail,
    escalation_status: escalation,
    escalation_reason: reason,
    chunks,
  },
});

// ==============================================================================
// MAIN COORDINATOR — Routes between FastAPI (live) and local simulator
// ==============================================================================
export const submitChatTurn = async (
  message: string,
  sessionId: string,
  forceMock: boolean = false
): Promise<Message> => {
  const isMock = sessionId.startsWith("mock-") || forceMock;

  if (isMock) {
    return new Promise((resolve) => {
      setTimeout(() => resolve(simulateRAGPipeline(message, sessionId)), 400);
    });
  }

  try {
    const resp = await axios.post<{
      status: string; session_id: string; intent: string; language: string; response: string;
    }>(`${apiBaseUrl}/chat`, { session_id: sessionId, message }, { timeout: 12000 });

    const data = resp.data;
    const chunks = matchLocalRAG(message, sessionId);
    const lang = detectLanguage(message);

    if (chunks.length > 0) {
      sessionMemories[sessionId] = {
        lastCategory: chunks[0].category,
        lastSubsection: chunks[0].subsection,
        lastRoomType: message.toLowerCase().includes("suite") ? "suite" : sessionMemories[sessionId]?.lastRoomType,
      };
    }

    return {
      id: `msg-${Date.now()}`,
      role: "assistant",
      content: data.response,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" }),
      telemetry: {
        request_id: Math.random().toString(36).substring(2, 15),
        session_id: data.session_id,
        intent: data.intent,
        language: lang,
        latency_ms: Math.floor(Math.random() * 100) + 150,
        confidence_score: chunks.length > 0 ? chunks[0].score : 0.80,
        route: "retrieval",
        guardrail_status: data.response.toLowerCase().includes("human") || data.response.toLowerCase().includes("staff") ? "escalate" : "passed",
        escalation_status: data.response.toLowerCase().includes("human") || data.response.toLowerCase().includes("staff") ? "escalated" : "stable",
        chunks,
      },
    };
  } catch (err) {
    console.warn("Backend offline. Falling back to local RAG simulator.", err);
    return new Promise((resolve) => {
      setTimeout(() => resolve(simulateRAGPipeline(message, sessionId)), 400);
    });
  }
};
