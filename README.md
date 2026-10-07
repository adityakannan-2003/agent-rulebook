# agent-rulebook

**The model proposes. The rulebook decides.**

![One night of an always-on agent, every action checked by the rulebook](post/night-log.png)

## What it does, in plain English

An AI agent is software that doesn't just answer questions. It takes actions: it refunds
orders, sends emails, buys supplies, deletes files.

That's useful, but it raises an obvious question: what stops it from doing something you
wouldn't have allowed? Asking the AI to "be careful" isn't a real answer, because the AI can
misunderstand or make a mistake, and nobody is watching at 3 AM.

This project puts a short list of rules between the AI and its actions. Before anything
happens, the rules give one of three answers:

| Answer | What happens | Examples |
|---|---|---|
| **Do it** | The action goes ahead. | Replying to one customer, a small refund, tidying up its own files |
| **Ask a person first** | The action waits until a human approves it. | A refund over $100, an email to more than 10 people |
| **Never** | The action is refused, and the AI is told why. | Spending more than $500 a day, deleting files outside its own folder, anything the rules don't mention |

The AI never gets to act directly. It can only *ask*, and plain code decides. The rules are
ordinary code, so you can read them, test them and change them. You can't do any of that
with a model's judgment.

## Who it's for

**Example: a small online shop owner.** Say you run a shop and want an AI assistant to
handle customer messages overnight. You're happy for it to answer "where's my order?" and
refund a $25 cracked mug on its own. You are *not* happy for it to refund $1,000, email your
whole customer list, or slash every price because sales were slow. With a rulebook, the routine
work gets done while you sleep, the big decisions wait for you in the morning, and the
dangerous ones can't happen at all.

The same idea helps:

- **Developers building agents** for support, operations or finance who need spending limits,
  approval steps and a safe default.
- **Team leads and product managers** who need to explain, concretely, what "a human in the
  loop" means before letting an agent near real customers or real money.

## Try it live

**[Agent Night Shift](https://claude.ai/artifact/SRzK53ZqHLMquWJJyfVzFc)** is a web page where a
real Claude agent works through a night's inbox for a made-up mug shop. Claude reads the
tickets and decides what to do. Every action it picks is a function call that goes through the
rulebook first:

- allowed actions happen in the simulated shop
- actions that need a person land in a "Waiting for you" list, where you approve or decline them
- blocked actions come back to Claude as an error, and it has to carry on without them

The shop, customers and money are made up, so nothing real is sent or spent. The decisions are
real: Claude's choices change from run to run, and the rules don't. You can add your own tickets
to see how it handles them. It runs on your own Claude account, so you need one to start the agent.

No Claude account? The page also keeps one saved real run. Anyone who opens it can watch what
the agent did, step by step, with **Play it back**.

## Run a real agent on your own computer (free, no API key)

`local_agent.py` runs the same night with a free open-source model on your machine, through
[Ollama](https://ollama.com). No account, no API key, no cost, and nothing leaves your computer.
The model decides what to do, and every action goes through the same `rulebook.py`.

1. Install Ollama from [ollama.com](https://ollama.com) and open it.
2. Download a small model that can use tools (about 2.5 GB):

   ```bash
   ollama pull qwen3:4b
   ```

3. Run the night shift:

   ```bash
   python3 local_agent.py
   ```

It prints each action with the rulebook's verdict, then the agent's morning note, then asks you
to approve or decline anything that's waiting. Try another model with `--model llama3.2:3b`.

Small models lose track when handed eight tasks at once, so the agent works one inbox item at a
time by default. A bigger model can take the whole inbox in one go with `--all-at-once`. On a Mac
with 8 GB of memory, a run with `qwen3:4b` can take several minutes.

Small models are slower and less careful than big ones. They sometimes skip a ticket or ask for
something odd. That's the point of the demo: the rules hold whichever model is proposing.

## Run the scripted version

`night_shift.py` replays one scripted night, so it gives the same result every time and needs
nothing installed. Python 3.9+.

```bash
python3 night_shift.py               # one scripted night, coloured log
python3 -m unittest -v               # all Python tests: the rulebook and the local agent
node --test live/rulebook.test.cjs   # the same 7 tests for the live page's rulebook, plus a match check
python3 post/build_images.py         # rebuild the images (needs Google Chrome)
```

## Files

- `rulebook.py`: the whole set of rules, 36 lines of Python
- `test_rulebook.py`: unit tests for the rules
- `local_agent.py`: a real agent on a free local model (Ollama), checked by the rulebook
- `test_local_agent.py`: tests for the local agent, using a stand-in model and a fake Ollama server
- `night_shift.py`: one scripted night for an online shop's support agent (11 actions)
- `live/index.html`: the live demo page, where Claude makes the decisions
- `live/rulebook.js`: the same rules in JavaScript; the live page carries an exact copy
- `live/rulebook.test.cjs`: the same 7 tests for the JavaScript rules, plus a check that the page's copy matches
- `post/`: the two images and the script that builds them from the real code

## Use it with your own agent

Call `decide()` in your tool layer, before any tool runs:

```python
decision = decide(action, spent_today)
if decision.verdict == "allow":
    result = run_tool(action)
elif decision.verdict == "ask":
    result = queue_for_approval(action, decision.reason)
else:
    result = f"Not allowed: {decision.reason}"   # tell the agent why, so it can adapt
```

The live page does exactly this in `act()` inside `live/index.html`.

## License

MIT, see [LICENSE](LICENSE).
