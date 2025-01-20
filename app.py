from flask import Flask, request, send_file, jsonify
from flask_cors import CORS
import subprocess
import os
import uuid
import time
from note_seq import midi_io

app = Flask(__name__)
CORS(app)

MODEL_DIR = os.path.join(os.getcwd(), 'model')  # Ścieżka do folderu z modelem
CHECKPOINT_PATH = os.path.join(MODEL_DIR, 'model.ckpt-100000')
TRANSCRIBE_SCRIPT = os.path.join(os.getcwd(), 'onsets_frames_transcription_transcribe.py')

# Tworzenie folderu tmp, jeśli nie istnieje
TMP_DIR = os.path.join(os.getcwd(), 'tmp')
os.makedirs(TMP_DIR, exist_ok=True)

# Mapowanie strun gitary na pitch pustej struny
guitar_strings = {
    6: 40,  # E (niska)
    5: 45,  # A
    4: 50,  # D
    3: 55,  # G
    2: 59,  # B
    1: 64   # E (wysoka)
}

def pitch_to_string_and_fret(pitch):
    options = []
    for string, base_pitch in guitar_strings.items():
        fret = pitch - base_pitch
        if 0 <= fret <= 24:
            options.append((string, fret))
    return min(options, key=lambda x: x[1]) if options else (None, None)

def get_note_duration_name(duration, seconds_per_beat):
    ratio = duration / seconds_per_beat
    if ratio >= 4:
        return "whole_note"
    elif ratio >= 2:
        return "half_note"
    elif ratio >= 1:
        return "quarter_note"
    elif ratio >= 0.5:
        return "eighth_note"
    elif ratio >= 0.25:
        return "sixteenth_note"
    else:
        return "thirty_second_note"

def group_notes_into_bars(tabulature, bar_duration):
    num_bars = int(max(note['start_time'] for note in tabulature) // bar_duration) + 1
    
    bars = [[] for _ in range(num_bars)]
    
    for note in tabulature:
        bar_number = int(note['start_time'] // bar_duration)
        bars[bar_number].append(note)
    
    return bars

def midi_to_tab(midi_path):
    note_sequence = midi_io.midi_file_to_sequence_proto(midi_path)
    tabulature = []
    tempo = note_sequence.tempos[0].qpm if note_sequence.tempos else 120
    numerator = note_sequence.time_signatures[0].numerator if note_sequence.time_signatures else 4
    denominator = note_sequence.time_signatures[0].denominator if note_sequence.time_signatures else 4
    seconds_per_beat = 60 / tempo
    bar_duration = numerator * seconds_per_beat

    for note in note_sequence.notes:
        string, fret = pitch_to_string_and_fret(note.pitch)
        duration = note.end_time - note.start_time
        note_duration_name = get_note_duration_name(duration, seconds_per_beat)
        if string is not None:
            tabulature.append({
                'start_time': note.start_time,
                'end_time': note.end_time,
                'string': string,
                'fret': fret,
                'duration_name': note_duration_name
            })

    bars = group_notes_into_bars(tabulature, bar_duration)
    return {
        'numerator': numerator,
        'denominator': denominator,
        'bars': bars
    }

@app.route('/transcribe', methods=['POST'])
def transcribe():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
    
    audio_file = request.files['audio']
    filename = f"temp_{uuid.uuid4()}.wav"
    audio_path = os.path.join(TMP_DIR, filename)
    audio_file.save(audio_path)

    try:
        subprocess.run([
            'python', TRANSCRIBE_SCRIPT,
            '--model_dir', MODEL_DIR,
            '--checkpoint_path', CHECKPOINT_PATH,
            '--hparams', 'spec_n_bins=80,spec_hop_length=512',
            audio_path
        ], check=True)
        
        midi_file = audio_path + '.midi'
        if not os.path.exists(midi_file):
            return jsonify({'error': 'MIDI file was not generated'}), 500
        
        tab_data = midi_to_tab(midi_file)
        return jsonify(tab_data), 200
    except subprocess.CalledProcessError as e:
        return jsonify({'error': str(e)}), 500
    finally:
        time.sleep(1)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
