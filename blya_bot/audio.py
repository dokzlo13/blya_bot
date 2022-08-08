import io
import pydub


# TODO: make converter really async
def convert_ogg_to_wav(ogg_buf: io.IOBase) -> io.BytesIO:
    audio: pydub.AudioSegment = pydub.AudioSegment.from_ogg(ogg_buf)
    audio = audio.set_channels(1)
    audio = audio.set_sample_width(2)

    wav_buf = io.BytesIO()
    audio.export(format="wav", out_f=wav_buf)
    wav_buf.seek(0)
    return wav_buf
