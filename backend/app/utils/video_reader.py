import base64
import os
import re
import subprocess
import ffmpeg
from PIL import Image, ImageDraw, ImageFont

from app.utils.logger import get_logger
from app.utils.path_helper import get_app_dir

logger = get_logger(__name__)

# 视频分段配置
SEGMENT_DURATION = 300  # 每段时长：5分钟（秒）

class VideoReader:
    def __init__(self,
                 video_path: str,
                 grid_size=(3, 3),
                 frame_interval=2,
                 unit_width=960,
                 unit_height=540,
                 save_quality=90,
                 font_path="fonts/arial.ttf",
                 frame_dir=None,
                 grid_dir=None):
        self.video_path = video_path
        self.grid_size = grid_size
        self.frame_interval = frame_interval
        self.unit_width = unit_width
        self.unit_height = unit_height
        self.save_quality = save_quality
        self.frame_dir = frame_dir or get_app_dir("output_frames")
        self.grid_dir = grid_dir or get_app_dir("grid_output")
        print(f"视频路径：{video_path}",self.frame_dir,self.grid_dir)
        self.font_path = font_path

    def format_time(self, seconds: float) -> str:
        mm = int(seconds // 60)
        ss = int(seconds % 60)
        return f"{mm:02d}_{ss:02d}"

    def extract_time_from_filename(self, filename: str) -> float:
        match = re.search(r"frame_(\d{2})_(\d{2})\.jpg", filename)
        if match:
            mm, ss = map(int, match.groups())
            return mm * 60 + ss
        return float('inf')

    def extract_frames(self, max_frames=1000) -> list[str]:

        try:
            os.makedirs(self.frame_dir, exist_ok=True)
            duration = float(ffmpeg.probe(self.video_path)["format"]["duration"])
            timestamps = [i for i in range(0, int(duration), self.frame_interval)][:max_frames]

            image_paths = []
            for ts in timestamps:
                time_label = self.format_time(ts)
                output_path = os.path.join(self.frame_dir, f"frame_{time_label}.jpg")
                cmd = ["ffmpeg", "-ss", str(ts), "-i", self.video_path, "-frames:v", "1", "-q:v", "2", "-y", output_path,
                       "-hide_banner", "-loglevel", "error"]
                subprocess.run(cmd, check=True)
                image_paths.append(output_path)
            return image_paths
        except Exception as e:
            logger.error(f"分割帧发生错误：{str(e)}")
            raise ValueError("视频处理失败")

    def group_images(self) -> list[list[str]]:
        image_files = [os.path.join(self.frame_dir, f) for f in os.listdir(self.frame_dir) if
                       f.startswith("frame_") and f.endswith(".jpg")]
        image_files.sort(key=lambda f: self.extract_time_from_filename(os.path.basename(f)))
        group_size = self.grid_size[0] * self.grid_size[1]
        return [image_files[i:i + group_size] for i in range(0, len(image_files), group_size)]

    def concat_images(self, image_paths: list[str], name: str) -> str:
        os.makedirs(self.grid_dir, exist_ok=True)
        font = ImageFont.truetype(self.font_path, 48) if os.path.exists(self.font_path) else ImageFont.load_default()
        images = []

        for path in image_paths:
            img = Image.open(path).convert("RGB").resize((self.unit_width, self.unit_height), Image.Resampling.LANCZOS)
            timestamp = re.search(r"frame_(\d{2})_(\d{2})\.jpg", os.path.basename(path))
            time_text = f"{timestamp.group(1)}:{timestamp.group(2)}" if timestamp else ""
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), time_text, fill="yellow", font=font, stroke_width=1, stroke_fill="black")
            images.append(img)

        cols, rows = self.grid_size
        grid_img = Image.new("RGB", (self.unit_width * cols, self.unit_height * rows), (255, 255, 255))

        for i, img in enumerate(images):
            x = (i % cols) * self.unit_width
            y = (i // cols) * self.unit_height
            grid_img.paste(img, (x, y))

        save_path = os.path.join(self.grid_dir, f"{name}.jpg")
        grid_img.save(save_path, quality=self.save_quality)
        return save_path

    def encode_images_to_base64(self, image_paths: list[str]) -> list[str]:
        base64_images = []
        for path in image_paths:
            with open(path, "rb") as img_file:
                encoded_string = base64.b64encode(img_file.read()).decode("utf-8")
                base64_images.append(f"data:image/jpeg;base64,{encoded_string}")
        return base64_images

    def run(self)->list[str]:
        logger.info("开始提取视频帧...")
        try:
            # 确保目录存在
            print(self.frame_dir,self.grid_dir)
            os.makedirs(self.frame_dir, exist_ok=True)
            os.makedirs(self.grid_dir, exist_ok=True)
            #清空帧文件夹
            for file in os.listdir(self.frame_dir):
                if file.startswith("frame_"):
                    os.remove(os.path.join(self.frame_dir, file))
            print(self.frame_dir,self.grid_dir)
            #清空网格文件夹
            for file in os.listdir(self.grid_dir):
                if file.startswith("grid_"):
                    os.remove(os.path.join(self.grid_dir, file))
            print(self.frame_dir,self.grid_dir)
            self.extract_frames()
            print("2#3",self.frame_dir,self.grid_dir)
            logger.info("开始拼接网格图...")
            image_paths = []
            groups = self.group_images()
            for idx, group in enumerate(groups, start=1):
                if len(group) < self.grid_size[0] * self.grid_size[1]:
                    logger.warning(f"⚠️ 跳过第 {idx} 组，图片不足 {self.grid_size[0] * self.grid_size[1]} 张")
                    continue
                out_path = self.concat_images(group, f"grid_{idx}")
                image_paths.append(out_path)

            logger.info("📤 开始编码图像...")
            urls = self.encode_images_to_base64(image_paths)
            return urls
        except Exception as e:
            logger.error(f"发生错误：{str(e)}")
            raise ValueError("视频处理失败")


def split_video_by_duration(input_video_path: str, output_dir: str = None, segment_duration: int = SEGMENT_DURATION) -> list[str]:
    """
    将视频按指定时长分段，返回所有分段文件路径列表

    Args:
        input_video_path: 输入视频路径
        output_dir: 输出目录（默认与输入文件同目录下的 segments 子目录）
        segment_duration: 每段时长（秒），默认5分钟

    Returns:
        分段视频文件路径列表，如果视频短于分段时长则返回原路径
    """
    try:
        # 获取视频时长
        probe = ffmpeg.probe(input_video_path)
        duration = float(probe["format"]["duration"])

        # 如果视频短于分段时长，直接返回原路径
        if duration <= segment_duration:
            logger.info(f"视频时长 {duration:.1f}秒，无需分段")
            return [input_video_path]

        # 创建分段输出目录
        if output_dir is None:
            base_dir = os.path.dirname(input_video_path)
            output_dir = os.path.join(base_dir, "segments")
        os.makedirs(output_dir, exist_ok=True)

        filename = os.path.basename(input_video_path)
        name, ext = os.path.splitext(filename)

        # 计算分段数量
        num_segments = int(duration // segment_duration) + (1 if duration % segment_duration > 0 else 0)
        logger.info(f"视频时长 {duration:.1f}秒，将分为 {num_segments} 段处理")

        segment_paths = []

        # 使用ffmpeg分段
        for i in range(num_segments):
            start_time = i * segment_duration
            output_path = os.path.join(output_dir, f"{name}_part{i+1:02d}{ext}")

            logger.info(f"生成第 {i+1}/{num_segments} 段：{start_time}s - {min(start_time + segment_duration, duration)}s")

            subprocess.run([
                "ffmpeg",
                "-i", input_video_path,
                "-ss", str(start_time),
                "-t", str(segment_duration),
                "-c", "copy",  # 复制编码，速度快
                "-y",  # 覆盖输出文件
                output_path
            ], check=True, capture_output=True)

            segment_paths.append(output_path)
            logger.info(f"第 {i+1}/{num_segments} 段完成：{output_path}")

        logger.info(f"视频分段完成，共 {len(segment_paths)} 段")
        return segment_paths

    except Exception as e:
        logger.error(f"视频分段失败：{e}")
        # 分段失败时返回原路径
        return [input_video_path]


