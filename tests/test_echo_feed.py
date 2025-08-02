from threading import Thread

from arianna_core.collective.echo_feed import EchoFeed


def test_echo_feed_trims_to_maxlen():
    feed = EchoFeed(maxlen=2)
    feed.add("a", {"n": 1})
    feed.add("b", {"n": 2})
    feed.add("c", {"n": 3})
    history = feed.last()
    assert len(history) == 2
    assert history[0]["text"] == "b"
    assert history[1]["text"] == "c"


def test_echo_feed_last_returns_copy():
    feed = EchoFeed(maxlen=3)
    feed.add("x", {})
    snapshot = feed.last()
    snapshot.append({"text": "y", "meta": {}})
    assert len(feed.last()) == 1


def test_echo_feed_thread_safety():
    feed = EchoFeed(maxlen=100)

    def worker(i: int) -> None:
        feed.add(str(i), {"i": i})

    threads = [Thread(target=worker, args=(i,)) for i in range(200)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(feed.last()) == 100
