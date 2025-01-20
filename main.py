from flask import Flask, request, send_file, jsonify
import subprocess
import os
import uuid
import time

app = Flask(__name__)

MODEL_DIR = os.path.join(os.getcwd(), 'model')  # Ścieżka do folderu z modelem
CHECKPOINT_PATH = os.path.join(MODEL_DIR, 'model.ckpt-100000')
TRANSCRIBE_SCRIPT = os.path.join(os.getcwd(), 'onsets_frames_transcription_transcribe.py')

# Tworzenie folderu tmp, jeśli nie istnieje
TMP_DIR = os.path.join(os.getcwd(), 'tmp')
os.makedirs(TMP_DIR, exist_ok=True)

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    filename = f"temp_{uuid.uuid4()}.wav"
    audio_path = os.path.join(TMP_DIR, filename)
    
    audio_file.save(audio_path)

    try:
        # Uruchomienie skryptu transkrypcji
        subprocess.run([
            'python', TRANSCRIBE_SCRIPT,
            '--model_dir', MODEL_DIR,
            '--checkpoint_path', CHECKPOINT_PATH,
            '--hparams', 'spec_n_bins=80,spec_hop_length=512,onset_length=24,offset_length=24,min_duration_ms=50,transform_audio=False,batch_size=1',
            audio_path
        ], check=True)
        
        midi_file = audio_path + '.midi'
        if not os.path.exists(midi_file):
            return jsonify({'error': 'MIDI file was not generated'}), 500
        
        response = send_file(midi_file, as_attachment=True, download_name='transcription.midi', max_age=0)
        time.sleep(1)  # Daj czas na zakończenie przesyłania
        return response
    except subprocess.CalledProcessError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        time.sleep(1)  # Daj czas na zamknięcie pliku


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
