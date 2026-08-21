"""音视频处理：把视频文件抽取音轨，供语音转写使用。"""
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

VIDEO_SUFFIXES = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".ts", ".flv", ".wmv"}


def is_video(suffix: str) -> bool:
    return (suffix or "").lower() in VIDEO_SUFFIXES


def extract_audio(file_bytes: bytes, suffix: str) -> tuple[bytes, str, str] | None:
    """从视频字节抽取 16kHz 单声道 WAV 音轨，返回 (bytes, filename, mime)。"""
    if not file_bytes:
        return None
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:  # noqa: BLE001
        logger.warning("imageio-ffmpeg 不可用，无法抽取视频音轨: %s", exc)
        return None

    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / f"input{suffix or '.mp4'}"
        dst = Path(tmp) / "audio.wav"
        src.write_bytes(file_bytes)
        cmd = [
            str(ffmpeg),
            "-y",
            "-i",
            str(src),
            "-vn",
            "-acodec",
            "pcm_s16le",
            "-ar",
            "16000",
            "-ac",
            "1",
            str(dst),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, timeout=300)
        except subprocess.TimeoutExpired:
            logger.warning("视频音轨抽取超时")
            return None
        if proc.returncode != 0 or not dst.exists() or dst.stat().st_size == 0:
            logger.warning("视频音轨抽取失败: %s", proc.stderr.decode("utf-8", "ignore")[:300])
            return None
        return dst.read_bytes(), "audio.wav", "audio/wav"
