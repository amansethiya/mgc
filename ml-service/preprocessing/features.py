from pathlib import Path
import numpy as np
import librosa
import soundfile as sf
from math import ceil
GENRES = ['blues','classical','country','disco','hiphop','jazz','metal','pop','reggae','rock']
CONFIG = {'sample_rate':22050,'max_seconds':30,'min_seconds':5,'n_mfcc':20,'n_fft':2048,'hop_length':512,'version':'features-v1'}
FEATURE_COUNT = 75
class InvalidAudio(ValueError): pass

def load_audio(path):
    try:
        with sf.SoundFile(path) as f:
            ext = Path(path).suffix.lower()
            if ext not in ('.wav','.mp3') or (ext == '.wav' and f.format not in ('WAV','WAVEX','RF64')) or (ext == '.mp3' and f.format not in ('MP3','MPEG')):
                raise InvalidAudio('Audio contents do not match a supported MP3 or WAV file.')
            rate=f.samplerate; duration=len(f)/rate
            if duration<CONFIG['min_seconds']:raise InvalidAudio('Audio must be at least 5 seconds long.')
            if not 8000<=rate<=192000 or not 1<=f.channels<=8:raise InvalidAudio('Unsupported sample rate or channel count.')
            data=f.read(min(len(f),ceil(rate*CONFIG['max_seconds'])),dtype='float32',always_2d=True)
        y=np.mean(data,axis=1,dtype=np.float32)
        if rate!=CONFIG['sample_rate']:y=librosa.resample(y,orig_sr=rate,target_sr=CONFIG['sample_rate'])
        if len(y)<CONFIG['sample_rate']*CONFIG['min_seconds'] or not np.isfinite(y).all() or np.max(np.abs(y))<1e-5:raise InvalidAudio('Audio is too short, silent or invalid.')
        return y,float(duration),float(min(duration,len(y)/CONFIG['sample_rate']))
    except InvalidAudio:raise
    except (OSError,RuntimeError,ValueError) as e:raise InvalidAudio('Unable to decode audio. Use a valid MP3 or WAV file.') from e

def extract_features(y):
    sr=CONFIG['sample_rate'];n=CONFIG['n_fft'];h=CONFIG['hop_length'];S=np.abs(librosa.stft(y,n_fft=n,hop_length=h));mel=librosa.feature.melspectrogram(S=S**2,sr=sr,n_fft=n,hop_length=h)
    matrices=[librosa.feature.mfcc(S=librosa.power_to_db(mel),n_mfcc=CONFIG['n_mfcc']),librosa.feature.chroma_stft(S=S**2,sr=sr,n_fft=n,hop_length=h),librosa.feature.spectral_centroid(S=S,sr=sr,n_fft=n),librosa.feature.spectral_bandwidth(S=S,sr=sr,n_fft=n),librosa.feature.spectral_rolloff(S=S,sr=sr,n_fft=n),librosa.feature.zero_crossing_rate(y,frame_length=n,hop_length=h),librosa.feature.rms(y=y,frame_length=n,hop_length=h)]
    tempo=float(np.asarray(librosa.feature.tempo(y=y,sr=sr,hop_length=h)).ravel()[0])
    vector=np.concatenate([v for a in matrices for v in (a.mean(axis=1),a.std(axis=1))]+[[tempo]]).astype(np.float32)
    if vector.shape!=(FEATURE_COUNT,) or not np.isfinite(vector).all():raise InvalidAudio('Audio features could not be calculated.')
    return vector
