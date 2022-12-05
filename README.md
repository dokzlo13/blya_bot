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

### Installing app dependencies

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

Current "blya_bot" implementation supports two different speech recognition engines: [vosk](https://github.com/alphacep/vosk-api) and [whisper](https://github.com/openai/whisper).

### Vosk

You can download models for `vosk` on this website - https://alphacephei.com/vosk/models

Place model in folder you like, and specify path to this model, on next step.

### Whisper

`Whisper` models will be downloaded automatically on first application start.

You can download it manually, by using links from [`whisper` repository](https://github.com/openai/whisper/blob/main/whisper/__init__.py#L17) (may be removed, just check Whisper source code for this).

Default models folder is `~/.cache/whisper`.

### Configure & run

When all dependencies installed and model files obtained, you need to configure settings.

Create `.env` file in this directory, and populate required options:

### Vosk

```env
TELEGRAM_BOT_TOKEN="<YOUR TOKEN>"

# At now, has only one option - `model_name`. Specify path to downloaded model
RECOGNITION_ENGINE_OPTIONS='{"model_path": "/path/to/vosk-model"}'
RECOGNITION_ENGINE="vosk"
```

```env
TELEGRAM_BOT_TOKEN="<YOUR TOKEN>"

# All options, except `language` will be passed into `whisper.load_model` function. Required fields: `model_name` and `language`
RECOGNITION_ENGINE_OPTIONS='{"model_name": "small", "language": "ru", "device": "cuda", "download_root": "~/.cache/whisper", "in_memory": False}'
RECOGNITION_ENGINE="whisper"
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

Building with [vosk](https://github.com/alphacep/vosk-api) speech recognition engine:

```
docker build -f ./images/Dockerfile-vosk-small-ru -t blya-bot-vosk:small-ru .
docker build -f ./images/Dockerfile-vosk-big-ru -t blya-bot-vosk:big-ru .
```

Running:

```
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-vosk:small-ru
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-vosk:big-ru
```

### Whisper - based

Building with [whisper](https://github.com/openai/whisper) speech recognition engine:

```
docker build -f ./images/Dockerfile-whisper-tiny-ru -t blya-bot-whisper:tiny-ru .
docker build -f ./images/Dockerfile-whisper-small-ru -t blya-bot-whisper:small-ru .
```

Running:

```
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-whisper:tiny-ru
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-whisper:small-ru
```


## TODO

- [x] Basic STT without external API's
- [x] Bad words counting and summarization
- [x] Highlight all bad words
- [x] Handle voice notes
- [x] Handle video notes
- [ ] Caching/storing transcriptions
- [x] Send transcription to chat
- [ ] Telegram webhook
- [ ] Configurable "transcribe" commands for bot
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
