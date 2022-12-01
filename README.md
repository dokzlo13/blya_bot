# blya_bot

[![Deploy to DigitalOcean](https://www.deploytodo.com/do-btn-blue.svg)](https://cloud.digitalocean.com/apps/new?repo=https://github.com/dokzlo13/blya_bot/tree/master/)

## Build & Run

### Vosk - based

Building with [vosk](https://github.com/alphacep/vosk-api) speech recognition core:

```
docker build -f ./Dockerfile-vosk -t blya-bot-vosk:latest .
```

Running:

```
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-vosk:latest
```

### Whisper - based

Building with [whisper](https://github.com/openai/whisper)  speech recognition core:

```
docker build -f ./Dockerfile-whisper -t blya-bot-whisper:latest .
```

Running:

```
docker run --env TELEGRAM_BOT_TOKEN="..." -p 8080:8080 blya-bot-whisper:latest
```


## TODO

- [x] Basic STT without external API's
- [x] Bad words counting and summarization
- [x] Highlight all bad words
- [x] Handle voice notes
- [x] Handle video notes
- [ ] Caching transcriptions
- [x] Send transcription to chat
- [ ] Telegram webhook

