# HTTP

## 1. Length mismatch between "r" and "rb" mode

`content-length` is measured in bytes by the server. Some non-ASCII characters (like curly quotes, em dashes, accented letters) are represented as multiple bytes in UTF-8. When Python decodes these in text mode, multiple bytes collapse into a single character. So the character count of the decoded string is smaller than the byte count the server promised.

## 2. read(n) in text mode reads n characters, not n bytes

In `"rb"` mode, `read(n)` reads n bytes — matching `content-length` exactly, no issue. In `"r"` mode, `read(n)` reads n characters. Since the character count of the decoded content is smaller than `content-length`, it hangs waiting for characters that never arrive, until the server's keep-alive timeout expires and it closes the connection.

## 3. Can't call connect() on an already connected socket

When you call `connect()`, the OS performs a TCP handshake and binds that file descriptor to a specific 4-tuple: source IP, source port, destination IP, destination port. That source port is now in use. Calling `connect()` again would require the OS to atomically tear down the existing connection and establish a new one on the same file descriptor, which it doesn't support. A new connection requires a new socket object. For example, imagine if the socket already has data in flight, letting you reconnect would lead to weird behavior.

## 4. Stale sockets and file descriptor exhaustion

A socket closed by the server has a broken underlying file descriptor and cannot be reused — calling `connect()` on it won't fix it. In long-running systems, unreleased stale file descriptors accumulate and can exhaust the file descriptor table. Production systems mitigate this with explicit cleanup, connection pool limits, and idle timeouts.

## 5. Python has no block scoping for if/else

Unlike Java or JavaScript, variables defined inside `if/else` blocks are accessible in the enclosing function scope. Instance attributes however must be initialized in `__init__` before they can be referenced in other methods.