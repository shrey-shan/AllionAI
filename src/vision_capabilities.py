# vision_capabilities.py
import asyncio, base64, time
from typing import Optional
from livekit import rtc
from livekit.agents import get_job_context
from livekit.agents.llm import ImageContent
from livekit.agents.utils.images import encode, EncodeOptions, ResizeOptions

class VisionCapabilities:
    """
    Drop-in vision helper that:
      • accepts images via byte stream channel "images"
      • buffers the latest frame from a remote video track (with FPS cap)
      • attaches the latest frame to the next user turn
      • cleans up tasks/streams on exit
    Mixin-friendly; call VisionCapabilities.__init__(self) in your subclass __init__.
    """
    def __init__(self) -> None:
        # Vision state
        self._latest_frame: Optional[str] = None  # data URL for LLM vision input
        self._video_stream: Optional[rtc.VideoStream] = None
        self._tasks: list[asyncio.Task] = []
        self._last_frame_ts: float = 0.0
        self._frame_interval_s: float = 0.2  # ~5 FPS
        self._max_upload_bytes: int = 8 * 1024 * 1024  # 8 MB

    # -------- lifecycle hooks --------
    async def on_enter(self):
        """Register byte-stream handler and attach to any existing video track."""
        room = get_job_context().room

        # Byte stream handler for images from FE (channel name: "images")
        def _image_received_handler(reader, participant_identity):
            task = asyncio.create_task(self._image_received(reader, participant_identity))
            self._tasks.append(task)
            task.add_done_callback(lambda t: self._safe_remove_task(t))

        room.register_byte_stream_handler("images", _image_received_handler)

        # Attach to an existing remote video track if present
        for participant in room.remote_participants.values():
            for publication in participant.track_publications.values():
                if publication.track and publication.track.kind == rtc.TrackKind.KIND_VIDEO:
                    self._create_video_stream(publication.track)
                    break

        # Watch for new video tracks
        @room.on("track_subscribed")
        def _on_track_subscribed(track: rtc.Track, publication: rtc.RemoteTrackPublication, participant: rtc.RemoteParticipant):
            if track.kind == rtc.TrackKind.KIND_VIDEO:
                self._create_video_stream(track)

    async def on_exit(self):
        """Close streams and cancel tasks."""
        if self._video_stream is not None:
            try:
                self._video_stream.close()
            except Exception:
                pass
            self._video_stream = None

        for t in list(self._tasks):
            if not t.done():
                t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def on_user_turn_completed(self, turn_ctx, new_message: dict) -> None:
        """Append the latest buffered video frame to the next user turn."""
        if self._latest_frame:
            if isinstance(new_message.content, list):
                new_message.content.append(ImageContent(image=self._latest_frame))
            elif new_message.content is None:
                new_message.content = [ImageContent(image=self._latest_frame)]
            else:
                new_message.content = [new_message.content, ImageContent(image=self._latest_frame)]
            self._latest_frame = None

    # -------- internals --------
    async def _image_received(self, reader, participant_identity):
        """Handle images uploaded from the frontend via byte stream."""
        buf = bytearray()
        read_bytes = 0
        try:
            async for chunk in reader:
                buf.extend(chunk)
                read_bytes += len(chunk)
                if read_bytes > self._max_upload_bytes:
                    # Too large; drop or log
                    return
        except Exception:
            return

        # If your FE can send/encode MIME type, use it; default to PNG otherwise.
        mime = "image/png"
        b64 = base64.b64encode(buf).decode("utf-8")

        chat_ctx = self.chat_ctx.copy()
        chat_ctx.add_message(
            role="user",
            content=[
                "Here's an image I want to share with you:",
                ImageContent(image=f"data:{mime};base64,{b64}"),
            ],
        )
        await self.update_chat_ctx(chat_ctx)

    def _create_video_stream(self, track: rtc.Track):
        """Subscribe to a single video stream and buffer the latest frame (with FPS cap)."""
        if self._video_stream is not None:
            try:
                self._video_stream.close()
            except Exception:
                pass
            self._video_stream = None

        self._video_stream = rtc.VideoStream(track)

        async def _read_stream():
            try:
                async for event in self._video_stream:
                    now = time.monotonic()
                    if (now - self._last_frame_ts) < self._frame_interval_s:
                        continue
                    self._last_frame_ts = now

                    image_bytes = encode(
                        event.frame,
                        EncodeOptions(
                            format="JPEG",
                            resize_options=ResizeOptions(
                                width=1024,
                                height=1024,
                                strategy="scale_aspect_fit",
                            ),
                        ),
                    )
                    self._latest_frame = "data:image/jpeg;base64," + base64.b64encode(image_bytes).decode("utf-8")
            except asyncio.CancelledError:
                pass
            except Exception:
                # swallow/log to keep agent alive
                pass

        task = asyncio.create_task(_read_stream())
        self._tasks.append(task)
        task.add_done_callback(lambda t: self._safe_remove_task(t))

    def _safe_remove_task(self, t: asyncio.Task):
        try:
            self._tasks.remove(t)
        except ValueError:
            pass
