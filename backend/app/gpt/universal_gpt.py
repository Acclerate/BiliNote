from app.gpt.base import GPT
from app.gpt.prompt_builder import generate_base_prompt
from app.models.gpt_model import GPTSource
from app.gpt.prompt import BASE_PROMPT, AI_SUM, SCREENSHOT, LINK
from app.gpt.utils import fix_markdown
from app.models.transcriber_model import TranscriptSegment
from datetime import timedelta
from typing import List
from app.utils.logger import get_logger
import json as json_module


class UniversalGPT(GPT):
    def __init__(self, client, model: str, temperature: float = 0.7):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.screenshot = False
        self.link = False
        self.logger = get_logger(__name__)
        self.logger.info(f"UniversalGPT initialized with model: {model}")
        self.logger.info(f"Client base_url: {getattr(client, 'base_url', 'unknown')}")

    def _format_time(self, seconds: float) -> str:
        return str(timedelta(seconds=int(seconds)))[2:]

    def _build_segment_text(self, segments: List[TranscriptSegment]) -> str:
        return "\n".join(
            f"{self._format_time(seg.start)} - {seg.text.strip()}"
            for seg in segments
        )

    def ensure_segments_type(self, segments) -> List[TranscriptSegment]:
        return [TranscriptSegment(**seg) if isinstance(seg, dict) else seg for seg in segments]

    def create_messages(self, segments: List[TranscriptSegment], **kwargs):

        content_text = generate_base_prompt(
            title=kwargs.get('title'),
            segment_text=self._build_segment_text(segments),
            tags=kwargs.get('tags'),
            _format=kwargs.get('_format'),
            style=kwargs.get('style'),
            extras=kwargs.get('extras'),
        )

        # ⛳ 组装 content 数组，支持 text + image_url 混合
        content = [{"type": "text", "text": content_text}]
        video_img_urls = kwargs.get('video_img_urls', [])

        for url in video_img_urls:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": url,
                    "detail": "auto"
                }
            })

        #  正确格式：整体包在一个 message 里，role + content array
        messages = [{
            "role": "user",
            "content": content
        }]

        return messages

    def list_models(self):
        return self.client.models.list()

    def summarize(self, source: GPTSource) -> str:
        self.screenshot = source.screenshot
        self.link = source.link
        source.segment = self.ensure_segments_type(source.segment)

        # 限制图片数量，避免请求过大
        max_images = 20
        original_images = source.video_img_urls or []
        limited_images = original_images[:max_images] if len(original_images) > max_images else original_images

        if len(original_images) > max_images:
            self.logger.warning(f"Images limited from {len(original_images)} to {max_images} to avoid request size issues")
            source.video_img_urls = limited_images

        messages = self.create_messages(
            source.segment,
            title=source.title,
            tags=source.tags,
            video_img_urls=source.video_img_urls,
            _format=source._format,
            style=source.style,
            extras=source.extras
        )

        self.logger.info(f"Sending request to model: {self.model}")
        self.logger.info(f"Number of segments: {len(source.segment)}")
        self.logger.info(f"Number of images: {len(source.video_img_urls or [])}")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=8192  # 限制响应长度
            )
            result = response.choices[0].message.content.strip()
            self.logger.info(f"Summarization successful, response length: {len(result)}")
            return result
        except Exception as e:
            self.logger.error(f"Summarization failed: {type(e).__name__}: {e}")
            # 记录请求详情用于调试
            self.logger.error(f"Request details - Model: {self.model}, Segments: {len(source.segment)}, Images: {len(source.video_img_urls or [])}")
            raise
