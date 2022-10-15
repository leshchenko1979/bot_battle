import uvicorn
from src.dispatcher import webserver

from logging import basicConfig

basicConfig(level="DEBUG")

def main():
    uvicorn.run(webserver.app, port=8200)


if __name__ == "__main__":
    main()
