# blya_bot

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/dokzlo13/blya_bot/tree/master/)

---

> Blya - Russian expletive "shit" (figuratively). Pronounced like "bla", but with a softer "L". It's what you might say if your car won't start in the morning, and you're going to be late for work. [urbandictionary](https://www.urbandictionary.com/define.php?term=blya)

This as a [telegram bot](https://core.telegram.org/bots/api), which transcribes voice and video notes into text, using automatic speech recognition (ASR) models with one purpose - decide, who uses more "curse words"...

## How it works?

This bot has 3 main parts:

- Speech recognition engine ([vosk](https://github.com/alphacep/vosk-api) and [whisper](https://github.com/openai/whisper))
- Dictionary generator with custom DSL and morphological expansion ([pymorphy2](https://github.com/kmike/pymorphy2)), which used to generate all variations of "abusive language" words
- Pattern Searching (based on Aho-Corasick Algorithm [ahocorapy](https://github.com/abusix/ahocorapy)), which used to find all "abusive language" words in transcribed text.

When bot starting, it loads dictionary file, which can be specified by user, and generates all words variants, by parsing dictionary's DSL.

Then, morphological analysis applied to each word. After this step, all morphological variants of this word will be added to dictionary.

Then, dictionary will be converted into Aho-Corasick automata, which will be used for pattern matching.

On next step, a speech recognition engine will be initialized. Application loads model into memory, and will be ready to process requests.

You can send voice or video note to this bot, and it will do following steps:

1. Transcribe voice into text
2. Search all "abusive language" words in transcribed text
3. Generate summary of used "abusive language" words
4. Bot Reply with "abusive language" words summary

You can also add your bot to the group, and it will automatically respond to all voice and video notes with "abusive language" summary.

## Limitations

Started as simple joke, this project was written especially for russian language.

Although speech recognition models support many languages, bot source code has some internal limitations. At this state, only russian language tested. Check [TODO](#todo) section for more information about multi-language support progress.

As example, morphological analysis is done by [pymorphy2](https://github.com/kmike/pymorphy2), which provides only russian morphological models.

If you want to try this bot with other language, just remove `pymorphy2` and `pymorphy2-dicts-ru` packages from installation. It will disable morphological analysis for dictionaries, but you will able to try bot on different speech recognition models.


## Dictionary DSL

```
#<anything> - Comment
!<word> - to disable morphing for this word. This token is global, and can be placed in any part of word.
  Expansions will also contain this token, and morphing will be disabled for variants too
~<word> - excludes word from dictionary. Applied after variants generation and morphing. Must be placed at word start.
[...|...] - expand to word with extra variants (suffixes, prefixes). 
  This will also include word without this elements, like: he[llo|ll] -> he, hello, hell
  Can be used with single variant only, like: bad[ass] -> bad, badass
{...|...} - expand to variants
  This will not include word without this elements, like: he{llo|ll} -> hello, hell
  Using single element in {} group has no sense, example: he{llo} -> hello
```

## Build & Run

### Install app dependencies

You can install blya-bot locally, with [poetry](https://python-poetry.org/):
```bash
$ # Virtualenv recommended:
$ python3 -m venv ./.venv
$ ./.venv/bin/activate
$ # Install Poetry, if you don't have it
$ pip install poetry
$ # Install blya-bot dependencies
$ poetry install --no-root --all-extras
```

### Obtaining speech recognition models

Next, you need to gather speech recognition model files.

Current "blya_bot" implementation supports multiple speech recognition engines:

- [vosk](https://github.com/alphacep/vosk-api)
- [whisper](https://github.com/openai/whisper) via [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
- [whisper](https://github.com/openai/whisper) via [pywhispercpp](https://github.com/abdeladim-s/pywhispercpp) bindings for [whisper.cpp](https://github.com/ggerganov/whisper.cpp)

#### Vosk

You can download models for `vosk` on this website - https://alphacephei.com/vosk/models

Place model in folder you like, and specify path to this model during configuration.

#### Faster-Whisper

Models will be downloaded automatically on first application start.

Default models folder is `~/.cache/huggingface/hub`.

#### Pywhispercpp

Models will be downloaded automatically on first application start.

Default models folder is `~/.local/share/pywhispercpp/models`.

### Configuration

When all dependencies installed and model files obtained, you need to configure settings.

Create `.env` file in this directory, and populate required options:

#### Vosk

```env
TELEGRAM_BOT_TOKEN="<YOUR TOKEN>"

RECOGNITION_ENGINE="vosk"
# At now, has only one option - `model_name`. Specify path to downloaded model
RECOGNITION_ENGINE_OPTIONS='{"model_path": "/path/to/vosk-model"}'
```

#### Faster-Whisper

```env
TELEGRAM_BOT_TOKEN="<YOUR TOKEN>"

RECOGNITION_ENGINE="faster-whisper"
# Required fields: `model` and `language`
RECOGNITION_ENGINE_OPTIONS='{"model": "small", "language": "ru", "device": "cpu", "compute_type": "int8", "beam_size": 5}'
```

#### Pywhispercpp


```env
TELEGRAM_BOT_TOKEN="<YOUR TOKEN>"

RECOGNITION_ENGINE="pywhispercpp"
# Required fields: `model` and `language`
RECOGNITION_ENGINE_OPTIONS='{"model": "small", "language": "ru"}'
```

When all required fields configured, you can run application:

```bash
$ python main.py # or python -m blya_bot
```

## Docker images

This repository also includes some docker-files, which can be used to build all-in-one `blya-bot` images.
This images will contain bot sources and desired speech recognition model.

Images can be distributed and will work without extra volumes.

### Vosk - based

Build:

Pass url to vosk model as `MODEL_URL` build arg.

```
docker build --build-arg MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-ru-0.22.zip" -t blya_bot:vosk -f dockerfiles/vosk.Dockerfile .
```

Run:

```
docker run --env TELEGRAM_BOT_TOKEN="..." blya_bot:vosk
```

### Faster-Whisper - based

Build:

Pass `MODEL` and `LANG` build args.

```
docker build --build-arg MODEL=small --build-arg LANG=ru -t blya_bot:faster-whisper -f dockerfiles/faster-whisper.Dockerfile .
```

Run:

```
docker run --env TELEGRAM_BOT_TOKEN="..." blya_bot:faster-whisper
```

### Pywhispercpp - based

Build:

Pass `MODEL` and `LANG` build args.

```
docker build --build-arg MODEL=small --build-arg LANG=ru -t blya_bot:pywhispercpp -f dockerfiles/pywhispercpp.Dockerfile .
```

Run:

```
docker run --env TELEGRAM_BOT_TOKEN="..." blya_bot:pywhispercpp
```

## TODO

- [x] Basic STT without external API's
- [x] Bad words counting and summarization
- [x] Highlight all bad words
- [x] Handle voice notes
- [x] Handle video notes
- [x] Caching/storing transcriptions
- [x] Send transcription to chat
- [ ] Telegram webhook
- [x] Configurable "transcribe" commands for bot
- [ ] Make bot "language independent"
  - [ ] Add other languages support for recognition
  - [ ] Add other languages support for morphological analysis
  - [ ] Summary templates
  - [ ] Remove all language-dependent parts from sources


## Contributing

1. Fork it
2. Clone it: `git clone https://github.com/dokzlo13/blya_bot.git`
3. Create your feature branch: `git checkout -b my-new-feature`
4. Make changes and add them: `git add .`
5. Commit: `git commit -m 'My awesome feature'`
6. Push: `git push origin my-new-feature`
7. Pull request
