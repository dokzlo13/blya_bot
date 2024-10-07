import argparse

import faster_whisper

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model", help="Model name", required=True)
    parser.add_argument("-o", "--out", help="Model path", default=None)

    args = parser.parse_args()
    print(f"Pulling model {args.model!r}...", flush=True)
    faster_whisper.download_model(size_or_id=args.model, output_dir=args.out if args.out else None)
    print("Model pulled!", flush=True)
