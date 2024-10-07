import argparse

from pywhispercpp.utils import download_model

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-m", "--model", help="Model name", required=True)
    parser.add_argument("-o", "--out", help="Model path", default=None)

    args = parser.parse_args()
    print(f"Pulling model {args.model!r}...", flush=True)
    download_model(model_name=args.model, download_dir=args.out if args.out else None)
    print("Model pulled!", flush=True)
