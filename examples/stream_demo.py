"""Feed a recorded answer to StreamNormalizer in small chunks and print each screen."""

from mathfence import StreamNormalizer

stream = StreamNormalizer()
for chunk in ["The fee is $", "5 and the tax is $", "10, area $x", "^2$."]:
    print(repr(stream.feed(chunk)))
print("final:", repr(stream.finish()))
