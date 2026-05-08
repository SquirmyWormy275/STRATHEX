* Tournament Workflow changes

    * Single Event Design stays EXACTLY the same
    * Needs to refelct the workflow of how a judge receives entry forms. 
    * Judges Typically receive a competitor's entry forms and input all of their events at once. They don't typically design an event and then find all of the competitor's entry forms for that event and then fill them in. (would be highly inefficient.)
    * For tournamnets, I want the ability to build the events first (as in select wood species/size quality/event format/numer of stands avaialable etc.) Then I want the ability to select ALL of the competitors for that day that have signed up. (and have a way to track whether or not they have apid their entry fees!) And then I want to be able to go competitor-by-competitor and select which of the events they will be entering in.
        * This means that the rough workflow will be something like this: Create all events for the day -> Select all competitors competiting in whole tournament -> go competitor by competitor and select which of the pre-made events they will compete in -> calculate handicaps -> analyze/review/approve handicaps -> generate heats/brackets -> generate entire day schedule -> input results -> track results/earnings.
    * please remeber that when creating an event, you will still need the exact number of stands, but not the number of competitors
    * this will neccessarily alter the way head-to-head brackets are created, but I am unsure of the best way to go about that

* Tournament Personnel management changes
    * I need a way to manage day-of scratches easily for the judge. If in normal events, simply remove them from the schedule. If they are in a bracket, then recalculate the bracket without them.

* Please optimize the entire Tournament Management (multi-event) system and menus for a human judge. Think about all of the ways you can streamline the workflow to make it easy and painless for a judge, showrunner, or even volunteer to take an individual entry form and use it to create the tournament. ALWAYS optimize for ease of use without eliminating the features or intent.


PREPARE FOR COMMIT — standing checklist

A standing checklist to run before each commit:
-Audit and update ALL documentation that needs to be altered to reflect changes made since last commit
-Audit and update documentation to reflect what is in the code, not just what previous documentation says
-Organize all new RELEVANT documentation
-Audit and update the "How this systems works" md that is accessible through the program to ensure that judges can access an accurate guide to understanding the project
-Clean/Scrub/eliminate erroneous, duplicative, and irrelevant documentation
-Clean/Scrub/eliminate erroneous, duplicative, and irrelevant development artifacts
-Update the Version Number across all files, filenames, other documentation, banners/ASCII art and remove all old version numbers
-Produce a professional commit message that reflects the project updates
-Roll any previously-agreed standing tasks (e.g., the older "Update documentation" rule) into this single Prepare for Commit pass so docs are updated once per commit rather than on every change.
