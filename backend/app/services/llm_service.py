"""
LLM 报告生成服务
支持：
  - mock 模式：不依赖 LLM API，直接生成模拟报告
  - OpenAI 兼容 API（DeepSeek、OpenAI、通义千问等）
  - Ollama 本地模型
"""
import os
import json
from typing import Dict, Any, Optional
from datetime import datetime


# ==================== Prompt 模板 ====================

IMAGE_REPORT_PROMPT = """
你是一名专业的动物健康检测AI助手。请根据以下图片检测结果，生成一份专业的动物健康分析报告。

## 检测信息
- 检测类型：图片检测
- 动物类型：{animal_type}
- 检测时间：{created_at}
- 检测模型：{model_name}

## 检测结果统计
- 检测目标总数：{total_targets} 个
- 正常目标：{normal_count} 个
- 可疑目标：{suspicious_count} 个
- 异常目标：{abnormal_count} 个

## 检测详情
{detections_detail}

请生成一份包含以下内容的报告：
1. **总体健康评估**：对本次检测结果的总体评价
2. **异常分析**：详细分析发现的异常和可疑情况
3. **健康建议**：针对检测结果提出的具体建议
4. **注意事项**：需要重点关注的问题

请用专业、清晰的语言生成报告，使用Markdown格式。
"""

VIDEO_REPORT_PROMPT = """
你是一名专业的动物健康检测AI助手。请根据以下视频检测结果，生成一份专业的动物健康跟踪分析报告。

## 检测信息
- 检测类型：视频检测
- 动物类型：{animal_type}
- 检测时间：{created_at}
- 检测帧数：{total_frames} 帧

## 跟踪统计
- 跟踪目标总数：{total_targets} 个
- 正常目标：{normal_count} 个
- 可疑目标：{suspicious_count} 个
- 异常目标：{abnormal_count} 个

## 跟踪轨迹详情
{tracks_detail}

请生成包含以下内容的报告：
1. **总体健康评估**
2. **目标跟踪分析**：各跟踪目标的行为和健康状态分析
3. **异常行为分析**：发现的异常行为描述
4. **健康建议**
5. **后续监测建议**

请用专业、清晰的语言生成报告，使用Markdown格式。
"""

CAMERA_REPORT_PROMPT = """
你是一名专业的动物健康检测AI助手。请根据以下实时摄像头检测记录，生成一份动物健康监测报告。

## 检测信息
- 检测类型：实时摄像头监测
- 动物类型：{animal_type}
- 检测时间：{created_at}

## 检测统计
- 处理帧数：{total_targets} 次检测
- 正常：{normal_count} 次
- 可疑：{suspicious_count} 次
- 异常：{abnormal_count} 次

请生成包含以下内容的监测报告：
1. **监测概况**
2. **健康状态分析**
3. **异常事件记录**
4. **改善建议**

请用专业、清晰的语言生成报告，使用Markdown格式。
"""


# ==================== Mock 报告模板 ====================

def _mock_report(detection_type: str, context: Dict[str, Any]) -> str:
    """生成模拟报告内容"""
    now = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    animal_type = context.get('animal_type', '未知动物')
    total = context.get('total_targets', 0)
    normal = context.get('normal_count', 0)
    suspicious = context.get('suspicious_count', 0)
    abnormal = context.get('abnormal_count', 0)

    health_level = "良好" if abnormal == 0 else ("需关注" if abnormal <= total * 0.2 else "警告")
    health_emoji = "✅" if abnormal == 0 else ("⚠️" if abnormal <= total * 0.2 else "🚨")

    return f"""# {animal_type}健康检测报告

**报告生成时间**：{now}  
**检测类型**：{'图片检测' if detection_type == 'image' else ('视频检测' if detection_type == 'video' else '实时监测')}  
**总体健康评级**：{health_emoji} {health_level}

---

## 一、总体健康评估

本次对{animal_type}进行{'图像' if detection_type == 'image' else '视频/实时'}检测，共检测到 **{total}** 个目标。
其中正常 **{normal}** 个，可疑 **{suspicious}** 个，异常 **{abnormal}** 个。

{'整体健康状况良好，未发现明显异常，建议继续保持当前饲养管理水平。' if abnormal == 0 else f'发现 {abnormal} 个目标存在异常状况，{suspicious} 个目标状态可疑，建议立即进行人工复查。'}

---

## 二、异常分析

{'本次检测未发现任何异常目标，所有检测对象健康状态正常。' if abnormal == 0 else f'''
检测发现以下问题：

- **异常目标数量**：{abnormal} 个（占总检测目标的 {abnormal/max(total,1)*100:.1f}%）
- **可疑目标数量**：{suspicious} 个（占总检测目标的 {suspicious/max(total,1)*100:.1f}%）
- **可能原因**：皮肤病变、肢体异常、行为异常等，需进一步人工检查确认
- **紧急程度**：{'高' if abnormal > total * 0.3 else '中'}
'''}

---

## 三、健康建议

1. **{'继续观察' if abnormal == 0 else '立即隔离'}**：{'建议每日观察动物状态，保持正常饲养管理。' if abnormal == 0 else f'对 {abnormal} 个异常目标进行隔离观察，防止疾病传播。'}
2. **环境管理**：保持养殖环境清洁卫生，定期消毒，控制温湿度在适宜范围内。
3. **饲料管理**：确保饲料营养均衡，供给充足清洁的饮水。
4. **定期检测**：建议每{'天' if detection_type == 'camera' else '周'}使用本系统进行健康检测，及时掌握动物健康状况。
{'5. **兽医会诊**：建议尽快联系专业兽医对异常个体进行检查和治疗。' if abnormal > 0 else ''}

---

## 四、注意事项

- 本报告基于AI视觉检测结果生成，仅供参考，不能替代专业兽医诊断
- 如发现动物出现精神萎靡、食欲下降、异常分泌物等症状，请立即联系兽医
- 建议结合人工巡检和本系统自动检测，形成完整的健康监测体系
- 检测结果受图像质量、光线条件、模型精度等因素影响

---

*本报告由动物健康监测系统自动生成（演示模式）*
"""


# ==================== LLM 调用 ====================

class LLMService:
    def __init__(self):
        self._client = None

    def _get_config(self, db=None) -> Dict[str, str]:
        """从数据库或环境变量获取 LLM 配置"""
        config = {
            'api_url': os.getenv('LLM_API_URL', ''),
            'api_key': os.getenv('LLM_API_KEY', ''),
            'model_name': os.getenv('LLM_MODEL_NAME', 'deepseek-chat'),
        }
        if db:
            try:
                from app.models.models import SystemConfig
                items = db.query(SystemConfig).filter(
                    SystemConfig.config_key.in_(['llm_api_url', 'llm_api_key', 'llm_model_name'])
                ).all()
                for item in items:
                    key = item.config_key.replace('llm_', '')
                    if item.config_value:
                        config[key.replace('_', '_')] = item.config_value
            except:
                pass
        return config

    def is_configured(self, db=None) -> bool:
        cfg = self._get_config(db)
        return bool(cfg.get('api_url') and cfg.get('api_key'))

    def generate_report(
        self,
        detection_type: str,
        context: Dict[str, Any],
        db=None
    ) -> str:
        """
        生成报告文本
        - 有 LLM 配置时调用真实 API
        - 无配置时返回 mock 报告
        """
        if not self.is_configured(db):
            return _mock_report(detection_type, context)

        cfg = self._get_config(db)
        prompt_map = {
            'image': IMAGE_REPORT_PROMPT,
            'video': VIDEO_REPORT_PROMPT,
            'camera': CAMERA_REPORT_PROMPT,
        }
        prompt_tpl = prompt_map.get(detection_type, IMAGE_REPORT_PROMPT)
        prompt = prompt_tpl.format(**{k: context.get(k, '') for k in [
            'animal_type', 'created_at', 'model_name', 'total_targets',
            'normal_count', 'suspicious_count', 'abnormal_count',
            'detections_detail', 'tracks_detail', 'total_frames'
        ] if '{' + k + '}' in prompt_tpl})

        try:
            import httpx
            headers = {
                'Authorization': f'Bearer {cfg["api_key"]}',
                'Content-Type': 'application/json',
            }
            payload = {
                'model': cfg['model_name'],
                'messages': [
                    {'role': 'system', 'content': '你是专业的动物健康检测AI助手，请用Markdown格式生成报告。'},
                    {'role': 'user', 'content': prompt}
                ],
                'temperature': 0.7,
                'max_tokens': 2000,
            }
            api_url = cfg['api_url'].rstrip('/') + '/chat/completions'
            resp = httpx.post(api_url, json=payload, headers=headers, timeout=60)
            resp.raise_for_status()
            data = resp.json()
            return data['choices'][0]['message']['content']
        except Exception as e:
            # API 调用失败时降级到 mock
            return _mock_report(detection_type, context) + f'\n\n*注：LLM API 调用失败（{str(e)[:100]}），已使用模板报告*'


llm_service = LLMService()
