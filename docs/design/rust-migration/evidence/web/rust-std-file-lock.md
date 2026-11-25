# Rust standard library: File::try_lock

URL: https://doc.rust-lang.org/stable/std/fs/struct.File.html
Retrieved: 2026-11-25T12:06:00Z
Tool: Context7 query-docs (/websites/doc_rust-lang_stable_std)
Processed: unknown
Data class: public

1. Signature (verbatim) - "pub fn try_lock(&self) -> Result<(), TryLockError>"
2. Contention (verbatim) - "Returns `Err(TryLockError::WouldBlock)` if a different lock is already held on this file (via another handle/descriptor)."
3. Platforms (verbatim) - "This function currently corresponds to the `flock` function on Unix with the `LOCK_EX` and `LOCK_NB` flags, and the `LockFileEx` function on Windows with the `LOCKFILE_EXCLUSIVE_LOCK` and `LOCKFILE_FAIL_IMMEDIATELY` flags."
4. Windows open mode (verbatim) - "On Windows, locking a file will fail if the file is opened only for append."
5. Release (verbatim) - "The lock will be released when this file (along with any other file descriptors/handles duplicated or inherited from it) is closed, or if the `unlock` method is called."
