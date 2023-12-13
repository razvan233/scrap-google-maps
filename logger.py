import logging


logging.basicConfig(
    filename='logs.log',
    level=logging.WARNING,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)


logger = logging.getLogger("GOOGLE MAPS SCRAPER")
