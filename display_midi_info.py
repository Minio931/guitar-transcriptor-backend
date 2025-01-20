from note_seq import midi_io
from note_seq.protobuf import music_pb2
import math

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
    """Znajduje najlepszą strunę i próg dla danego pitch."""
    options = []
    for string, base_pitch in guitar_strings.items():
        fret = pitch - base_pitch
        if 0 <= fret <= 24:  # Zakres progów
            options.append((string, fret))
    # Wybierz najwygodniejsze (najniższy próg)
    return min(options, key=lambda x: x[1]) if options else (None, None)

def get_note_duration_name(duration, seconds_per_beat):
    """Określa nazwę wartości rytmicznej nuty."""
    ratio = duration / seconds_per_beat
    if ratio >= 4:
        return "cała nuta"
    elif ratio >= 2:
        return "półnuta"
    elif ratio >= 1:
        return "ćwierćnuta"
    elif ratio >= 0.5:
        return "ósemka"
    elif ratio >= 0.25:
        return "szesnastka"
    else:
        return "trzydziestodwójka"

def group_notes_into_bars(tabulature, bar_duration):
    """Grupuje nuty w takty na podstawie długości taktu."""
    bars = {}
    for note in tabulature:
        bar_number = int(note['start_time'] // bar_duration)
        if bar_number not in bars:
            bars[bar_number] = []
        bars[bar_number].append(note)
    return bars

def display_midi_as_tab(midi_path):
    """Konwertuje plik MIDI na tabulaturę gitarową z podziałem na takty i określeniem wartości rytmicznych."""
    note_sequence = midi_io.midi_file_to_sequence_proto(midi_path)
    tabulature = []

    # Pobranie tempa i metrum
    tempo = note_sequence.tempos[0].qpm if note_sequence.tempos else 120  # Domyślnie 120 BPM
    numerator = note_sequence.time_signatures[0].numerator if note_sequence.time_signatures else 4
    denominator = note_sequence.time_signatures[0].denominator if note_sequence.time_signatures else 4

    # Obliczenie długości taktu w sekundach
    beats_per_bar = numerator
    seconds_per_beat = 60 / tempo
    bar_duration = beats_per_bar * seconds_per_beat

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

    # Grupowanie nut w takty
    bars = group_notes_into_bars(tabulature, bar_duration)
    
    # Wyświetlenie tabulatury z podziałem na takty i wartości rytmicznej
    for bar_number in sorted(bars.keys()):
        print(f"\nTakt {bar_number + 1}:")
        for note in sorted(bars[bar_number], key=lambda x: x['start_time']):
            print(f"  Struna: {note['string']}, Próg: {note['fret']}, Start: {note['start_time']:.2f}s, Wartość rytmiczna: {note['duration_name']}")

# Ścieżka do pliku MIDI
midi_file_path = './tmp/temp_2e9dbd71-3433-4654-8c0c-256816f72638.wav.midi'  # Zmień na swoją ścieżkę

display_midi_as_tab(midi_file_path)