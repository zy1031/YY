"""
视频/实时健康判定规则
只服务于视频与实时监控场景，不用于图片行为识别。
"""
from typing import Dict, Iterable, List, Optional

HEALTH_RULE_KEYWORDS = {
    "abnormal": [
        "dead", "dying", "severe", "fracture", "bleeding", "convulsion",
        "paralysis", "unable", "collapse", "down", "infected", "infection",
        "pneumonia", "fever", "mastitis", "lameness", "injury", "wound",
        "disease", "lesion", "ulcer", "scab", "diarrhea", "vomit", "abnormal",
        "sick", "pig_skin_disease", "sheep_scab",
    ],
    "suspicious": [
        "cough", "pant", "panting", "fatigue", "lethargy", "slow", "limp",
        "thin", "hunched", "reduced", "weak", "isolate", "isolated",
        "scratching", "itch", "restless", "fever_risk", "risk", "suspect",
        "suspicious",
    ],
}

ABNORMAL_BEHAVIOR_KEYWORDS = [
    "fall", "fallen", "collapse", "stagger", "limp", "lameness", "tremor",
    "convulsion", "unable_to_stand", "dragging", "seizure",
]

SUSPICIOUS_BEHAVIOR_KEYWORDS = [
    "restless", "scratching", "hunched", "crowding", "isolation", "reduced_movement",
    "slow_movement", "panting", "coughing", "head_shake",
]

SPECIES_RULES = {
    "羊": {
        "normal": ["活动", "进食", "躺卧", "walking", "running", "standing", "eating", "drinking", "lying"],
        "suspicious": [],
        "abnormal": [],
    },
}


def _contains_keyword(text: str, keywords: Iterable[str]) -> bool:
    value = text.lower()
    return any(keyword.lower() in value for keyword in keywords)


def classify_health_status(class_name: str, confidence: float) -> str:
    """基于类别名称和置信度做单目标健康判定。"""
    name = class_name.lower()

    if _contains_keyword(name, HEALTH_RULE_KEYWORDS["abnormal"]):
        return "abnormal" if confidence >= 0.6 else "suspicious"

    if _contains_keyword(name, HEALTH_RULE_KEYWORDS["suspicious"]):
        return "suspicious"

    return "normal"


def classify_behavior_risk(behavior_name: str, confidence: float) -> str:
    """当模型偏行为标签时，根据行为模式映射为健康风险。"""
    name = behavior_name.lower()

    if _contains_keyword(name, ABNORMAL_BEHAVIOR_KEYWORDS):
        return "abnormal" if confidence >= 0.55 else "suspicious"

    if _contains_keyword(name, SUSPICIOUS_BEHAVIOR_KEYWORDS):
        return "suspicious"

    return "normal"


def classify_species_behavior(species_name: Optional[str], class_name: str, confidence: float) -> str:
    """按物种数据集标签做业务映射。"""
    if not species_name:
        return "normal"

    rules = SPECIES_RULES.get(species_name)
    if not rules:
        return "normal"

    label = class_name.lower()

    if _contains_keyword(label, rules.get("abnormal", [])):
        return "abnormal" if confidence >= 0.55 else "suspicious"

    if _contains_keyword(label, rules.get("suspicious", [])):
        return "suspicious"

    if _contains_keyword(label, rules.get("normal", [])):
        return "normal"

    return "normal"


def merge_health_and_behavior(class_name: str, confidence: float, species_name: Optional[str] = None) -> str:
    """综合类别语义、行为语义和物种标签规则，取风险较高的结果。"""
    primary = classify_health_status(class_name, confidence)
    behavior = classify_behavior_risk(class_name, confidence)
    species_status = classify_species_behavior(species_name, class_name, confidence)
    order = {"normal": 0, "suspicious": 1, "abnormal": 2}
    return max([primary, behavior, species_status], key=lambda status: order[status])


def summarize_track_health(statuses: List[str], abnormal_threshold: float = 0.3, suspicious_threshold: float = 0.4) -> str:
    """按轨迹聚合健康状态，避免单帧抖动。"""
    if not statuses:
        return "normal"

    total = len(statuses)
    abnormal_count = sum(1 for status in statuses if status == "abnormal")
    suspicious_count = sum(1 for status in statuses if status == "suspicious")

    if abnormal_count / total >= abnormal_threshold or abnormal_count >= 2:
        return "abnormal"

    if suspicious_count / total >= suspicious_threshold or (abnormal_count + suspicious_count) / total >= 0.5:
        return "suspicious"

    return "normal"


def summarize_counts_from_tracks(track_summaries: List[Dict]) -> Dict[str, int]:
    counts = {"normal": 0, "suspicious": 0, "abnormal": 0}
    for summary in track_summaries:
        status = summary.get("health_status_summary", "normal")
        counts[status] = counts.get(status, 0) + 1
    return counts
