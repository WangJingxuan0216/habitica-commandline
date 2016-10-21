## Habitica Command Line Version

### Abstract
This tool is updated from a version created by philadams(https://github.com/philadams/habitica) according to newly update on API v3.

### Available Functions
Usage: habitica [--version] [--help]
                    <command> [<args>...] [--dif=<d>] [--date=<d>] [--task=<d>]
                    [--verbose | --debug]

    Options:
      -h --help         Show this screen
      --version         Show version
      --dif=<d>         (easy | medium | hard) [default: easy]
      --date=<d>        [default: None]
      --task=<d>        [default: -1]
      --verbose         Show some logging information
      --debug           Some all logging information

    The habitica commands are:
      status                  Show HP, XP, GP, and more
      habits                  List habit tasks
      habits up <task-id>     Up (+) habit <task-id>
      habits down <task-id>   Down (-) habit <task-id>
      dailies                 List daily tasks
      dailies done            Mark daily <task-id> complete
      dailies undo            Mark daily <task-id> incomplete
      todos                   List todo tasks
      todos done <task-id>    Mark one or more todo <task-id> completed
      todos done <task-id>.<checklist-id> Mark one todo <checklist-id> in <task-id> completed
      todos add <task>        Add todo with description <task>
      todos add_cl <task-id>  Add checklist item with description <task>
      server                  Show status of Habitica service
      home                    Open tasks page in default browser
      pet                     Check pet and feed if possible
      egg                     Check egg and hatch if possible
      sleep                   Check sleeping status and moving in/leaving inn

### Examples

### Authors and Contributors 
Special thanks to @philadams

### To-do List
- [ ] function for mounting
- [ ] quest is not showing correctly in status
- [ ] feeding food doesn't work
