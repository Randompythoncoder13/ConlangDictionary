import soundfile as sf
import numpy as np
from kokoro import KPipeline


def synthesize_ipa_to_file(ipa_string, voice_name, output_filename):
    print(f"Initializing Kokoro pipeline... (This may take a moment)")

    try:
        pipeline = KPipeline(lang_code='a')
    except Exception as e:
        print(f"Error initializing KPipeline: {e}")
        print("This often happens if 'espeak-ng' is not installed or not in your system's PATH.")
        return

    text_with_ipa = f"[This is an IPA test]({ipa_string})"

    print(f"Synthesizing IPA: {ipa_string}")
    print(f"Using voice: {voice_name}")

    audio_chunks = []

    generator = pipeline(text_with_ipa, voice=voice_name)

    for i, (gs, ps, audio) in enumerate(generator):
        print(f"  - Received audio chunk {i}")
        audio_chunks.append(audio)

    if not audio_chunks:
        print("Error: No audio was generated.")
        return

    final_audio = np.concatenate(audio_chunks)

    samplerate = 24000
    sf.write(output_filename, final_audio, samplerate)

    print(f"\nSuccess! Audio saved to: {output_filename}")


if __name__ == "__main__":
    ipa_to_synthesize = "/həlˈə͡ʊ wˈɜːld!  ðˈɪs ˈɪz ˈe͡ɪ tˈɛst ˈɒv ðˈə ˌa͡ɪpˌiːˈe͡ɪ tˈɛkst tˈuː spˈiːt͡ʃ sˈɪstəm./"
    voice_to_use = "af_heart"
    output_file = "kokoro_ipa_test.wav"

    synthesize_ipa_to_file(ipa_to_synthesize, voice_to_use, output_file)
