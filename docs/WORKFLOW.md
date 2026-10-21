# How the application agent works, in simple words

Think of the agent as an assistant with a fact sheet and a locked send button.

1. **Read the fact sheet.** A saved candidate profile contains a made-up person's name, contact details, education, jobs, skills, resume, and answers they have already checked.
2. **Open the application.** For this first version, the application is a pretend employer's form running on this computer. No real employer receives anything.
3. **Read each question.** The agent looks at the labels next to the boxes: “Full name,” “Email address,” “School,” and so on.
4. **Look for a known answer.** If the profile has one clear answer, the agent enters it. It does not write a story or guess missing details.
5. **Attach the resume.** The agent checks that the file is the expected file, then attaches it through the browser.
6. **Leave unknown answers empty.** The example profile has no salary request or reason for wanting the job. Those boxes stay empty. A list asks the person to supply and check those answers before a later run.
7. **Check the work.** The program reads the boxes back. A separate answer key checks that the pretend form is correct, including the boxes that should be empty.
8. **Stop for review.** Normally the run ends here. If started with `--review`, the person sees the answers and must type an exact approval phrase before the pretend application can be sent. Changing an answer invalidates that approval.
9. **Save a record.** Screenshots and a step-by-step action log show what happened. These records will help compare future agent versions and prepare training data.

## Where the AI model fits

OpenWebRL supplies the browser environment: the machinery that clicks, types, and takes screenshots. The application agent currently uses simple matching rules to choose profile answers. This keeps the first version predictable.

A separate test gives a small pretrained AI model a screenshot and asks what word to type into a box that is already selected. The model supplies the word, and OpenWebRL types it. That test passed without teaching or retraining the model. It is a small first check, not proof that the model can handle every application.

## What “RL-ready” means here

Reinforcement learning means improving an agent by giving it feedback about its actions. This version saves actions, screenshots, and correctness checks so future work can use them. It does not run reinforcement learning. Some application-specific actions still need to be connected to OpenWebRL's training tools before those records can be used for training.

## How a person adds a missing answer

Open the synthetic profile file, add the exact question and its answer under `verified_answers`, mark it checked, and record who checked it and when. Run the agent again. If the question remains unclear, leave it blank and review it yourself.
