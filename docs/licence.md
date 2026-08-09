# Licensing the engine

The panel needs no licence — it is open source and updates itself from a public channel. The
**engine** is the licensed part: until this machine has been logged in, it refuses to start and
says so.

## What you need before you start

Two things, and neither of them ends up on this machine:

* your **licence key**,
* the **email address the licence was issued to**.

There is no public sign-up. If you have the engine but no key, the owner is who to ask.

You do not need a server address. A released engine carries the address of the login page; that
is part of the build, not part of your configuration.

## How it works, in one paragraph

You open our login page in a browser **once**, type the key and the email there, and the page
prints a **licence string** — a line beginning `lt_`. You hand that string to the engine, and
that is the end of your part. From then on the machine renews itself: it holds the string on
disk, shows it to the licence service, and gets the next one back together with a fresh copy of
the licence. **The key and the email never reach this machine** — not the config file, not the
disk. They belong in the browser.

## Activating from the panel

The engine row carries a **key button**. Press it and a small window opens.

1. The window prints the address of the login page. Open it in a browser — any machine will do,
   it does not have to be this one.
2. On that page, type your licence key and the email the licence was issued to. It answers with
   a string starting `lt_`.
3. Paste the string into the window and press **Activate**.

The window shows you the engine's own answer. On success it says the machine is licensed and
will renew by itself; then press **Start** on the engine row.

The button belongs to a row, not to the machine: it logs in the engine **that row starts**. If a
row cannot be logged in — because it launches a script rather than an engine — the panel refuses
before the window opens and says why on the row you pressed.

## Activating without the panel

The same thing, on the command line, for a machine with no screen:

```bash
letapis license activate                 # prints the login address, exits 2
letapis license activate lt_...          # hands over the string, exits 0
cat string.txt | letapis license activate   # same, without the shell history keeping it
```

## Checking that it took

In the engine's data directory there is a `license/` folder with a `current` pointer, and in the
directory it names, two files:

```
license.json   the signed licence
token.json     the string, and the moment it stops being good
```

Two files, not three. A `receipt.json` there means the machine is running an **old** engine from
before this scheme — the way forward is a newer engine and a fresh login.

## Living with it afterwards

| What | How it behaves |
|---|---|
| How long the string is good for | **7 days**, decided by the licence service |
| When the engine asks | at **every start**, and before an engine update — never while it is running |
| What comes back | the next string and a fresh copy of the licence, checked before anything is written |
| Service unreachable | the engine keeps working until the string's 7 days run out, and warns |
| Licence revoked | the refusal arrives at the **next start or update**; a running engine keeps running until it is restarted |

There is no weekly login. A machine nobody touches keeps working on its own.

**Do not copy the data directory to a second machine.** Both will work — until the string is
renewed. Then one of them gets the new string and the other is refused, and you will not know
which one it will be until it happens.

## When you need a person again

Three cases only: the data directory was lost along with the string · the licence was revoked and
a new one issued · another machine (a copy) renewed the string first. In all three you log in
again.

## When it refuses

The engine answers in sentences, not codes. Each one names a **different next step**:

| What you read | What happened | What to do |
|---|---|---|
| *this machine has not been logged in yet* | nothing has been handed over — the engine has never been to the service | activate it, above |
| *the licence service could not be reached* | we went, nobody answered, and the string had already run out | put the machine on the network |
| *this machine has been unable to reach us for too long* | the 7 days ran out while offline | put the machine on the network |
| *the string this machine holds was not accepted* | the service said no — a copy may have renewed it first | log in again |
| *the licence was not recognised* | the licence is not in the service's list: revoked, expired or removed — all three look alike | check the key was typed correctly; if it was, ask the owner |
| *this build does not know where the licence server is* | the engine was built without a login address | the kit is faulty; configuration cannot fix it |

## What the panel's lamp does and does not say

The lamp answers **"is the engine alive"** and nothing else. An engine that starts and then
refuses work for licence reasons is not a service fault — and an engine that never got past the
licence gate does not start at all, so the row simply stays dark.

Either way the engine's own words are in its log, `/tmp/letapis-core.log`, one click away on the
row.
