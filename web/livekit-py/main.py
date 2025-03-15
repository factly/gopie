import asyncio
import logging

from dotenv import load_dotenv
from livekit import rtc
from livekit.agents import (
    AutoSubscribe,
    JobContext,
    WorkerOptions,
    cli,
    stt,
    transcription,
)
from livekit.plugins import openai, silero

load_dotenv()

logger = logging.getLogger("transcriber")
logger.setLevel(logging.INFO)


async def _forward_transcription(
    stt_stream: stt.SpeechStream, stt_forwarder: transcription.STTSegmentsForwarder
):
    """Forward the transcription to the client and log the transcript in the console"""
    async for ev in stt_stream:
        if ev.type == stt.SpeechEventType.INTERIM_TRANSCRIPT:
            # you may not want to log interim transcripts, they are not final and may be incorrect
            pass
        elif ev.type == stt.SpeechEventType.FINAL_TRANSCRIPT:
            print(" -> ", ev.alternatives[0].text)
        elif ev.type == stt.SpeechEventType.RECOGNITION_USAGE:
            logger.debug(f"metrics: {ev.recognition_usage}")

        stt_forwarder.update(ev)


async def _handle_text_message(text: str, tts: openai.TTS, source: rtc.AudioSource):
    """Handle incoming text messages by converting them to speech"""
    logger.info(f'Converting text to speech: "{text}"')
    async for output in tts.synthesize(text):
        await source.capture_frame(output.frame)


async def entrypoint(ctx: JobContext):
    logger.info("starting transcriber and TTS agent")

    # Set up STT
    stt_impl = openai.STT()
    if not stt_impl.capabilities.streaming:
        stt_impl = stt.StreamAdapter(
            stt=stt_impl,
            vad=silero.VAD.load(
                min_silence_duration=0.3,
            ),
        )

    # Set up TTS
    tts = openai.TTS(model="tts-1", voice="nova")
    source = rtc.AudioSource(tts.sample_rate, tts.num_channels)
    tts_track = rtc.LocalAudioTrack.create_audio_track("agent-tts", source)
    options = rtc.TrackPublishOptions()
    options.source = rtc.TrackSource.SOURCE_MICROPHONE

    async def transcribe_track(participant: rtc.RemoteParticipant, track: rtc.Track):
        audio_stream = rtc.AudioStream(track)
        stt_forwarder = transcription.STTSegmentsForwarder(
            room=ctx.room, participant=participant, track=track
        )

        stt_stream = stt_impl.stream()
        asyncio.create_task(_forward_transcription(stt_stream, stt_forwarder))

        async for ev in audio_stream:
            stt_stream.push_frame(ev.frame)

    @ctx.room.on("track_subscribed")
    def on_track_subscribed(
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            asyncio.create_task(transcribe_track(participant, track))

    @ctx.room.on("data_received")
    def on_message_received(data_packet: rtc.DataPacket):
        # Handle incoming text messages for TTS
        print("Received data packet: ", data_packet.data)
        asyncio.create_task(
            _handle_text_message(data_packet.data.decode(), tts, source)
        )

    # Connect and publish TTS track
    await ctx.connect(auto_subscribe=AutoSubscribe.AUDIO_ONLY)
    publication = await ctx.room.local_participant.publish_track(tts_track, options)
    await publication.wait_for_subscription()
    logger.info("TTS track published and ready")


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint))
