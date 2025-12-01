import sys
import os
import re

class OATMEALInterpreter:
    """
    OATMEAL Interpreter - An esoteric programming language based on oatmeal bowls 

    The language uses a tape of unbounded positive integers with limited size at a time. 
    Each cell corresponds to a bowl of oatmeal.
    """

    def __init__(self):
        # The language processes a tape of integers, so we need an array to represent the tape
        # In oatmeal terms, this is a list of bowls of oatmeal
        self.tape = []
        
        # The language uses a data pointer to indicate which cell/bowl is being modified 
        # We'll just use an index tracker 
        self.data_pointer = 0

        # I didn't mention it in the video but we need an instruction pointer to track where we are in the program 
        # This is just another index tracker 
        self.instruction_pointer = 0

        # We'll need a stack for function calls and loops 
        self.call_stack = []

        # We'll need to define functions
        self.functions = {}

        # We'll need to keep track of which cells are marked as read-only
        # We can save space by using a set 
        self.readonly_cells = set()

        # Stack of tupes for nested /\ scopes 
        # Tracks the RANGES where ' commands can jump within
        self.loop_scopes = []

        # Needed for preceding > to validate " command 
        self.previous_was_right = False

        # Program to be executed 
        self.program = ""

    # Get the current value in a cell
    def get_cell_value(self, position):
        # Checking to make sure the position we are asking for is within the bounds of the tape
        if 0 <= position < len(self.tape):  
            return self.tape[position]
        else:
            # We are off the tape, so we are just going to return a default value 
            return 0 
        
    # Set the current value in a cell 
    def set_cell_value(self, position, value):
        if 0 <= position < len(self.tape) and position not in self.readonly_cells:
            self.tape[position] = max(0, value)  # Ensure non-negative
    
    # Helper function
    def is_on_tape(self):
        return 0 <= self.data_pointer < len(self.tape)

    # Move right, while wrapping around
    def move_data_pointer_right(self):
        if len(self.tape) == 0:
            # No cells on tape, must create first cell 
            self.data_pointer = 0
        else:
            self.data_pointer += 1
            if self.data_pointer > len(self.tape):
                self.data_pointer = -1
    
    # Move left, while wrapping around 
    def move_data_pointer_left(self):
        # Logic is very pretty much the same as the right function
        if len(self.tape) == 0:
            # No cells on tape, must create first cell 
            self.data_pointer = 0
        else:
            self.data_pointer -= 1
            if self.data_pointer < -1:
                self.data_pointer = len(self.tape)

    # Increment current cell
    def increment_cell(self):
        # Making sure we are actually on the tape 
        # Since we work with positive unbounded integers we have no check for the number 
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            self.tape[self.data_pointer] += 1
    
    # Decrement current cell
    def decrement_cell(self):
        # Making sure we are actually on the tape
        # Since we only work with positive integers, we have to do no-op on negative integers
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            if self.tape[self.data_pointer] > 0:
                self.tape[self.data_pointer] -= 1

    # Insert a new cell at the data pointer position 
    def insert_cell_command(self):
        if len(self.tape) == 0:
            # First cell
            self.tape = [0]
            self.data_pointer = 0
        elif self.data_pointer == -1:
            # Before first - insert at beginning
            self.tape.insert(0, 0)
            self.data_pointer = 0
            # Adjust read-only indices
            self.readonly_cells = {i + 1 for i in self.readonly_cells}
        elif self.data_pointer >= len(self.tape):
            # After last - append
            self.tape.append(0)
            self.data_pointer = len(self.tape) - 1
        else:
            # Insert at current position, shift right
            self.tape.insert(self.data_pointer, 0)
            # Adjust read-only indices for cells that shifted
            new_readonly = set()
            for i in self.readonly_cells:
                if i >= self.data_pointer:
                    new_readonly.add(i + 1)
                else:
                    new_readonly.add(i)
            self.readonly_cells = new_readonly
    
    # Helper function
    def find_matching_backslash(self, start_pos):
        depth = 1
        pos = start_pos + 1
        while pos < len(self.program) and depth > 0:
            if self.program[pos] == '/':
                depth += 1
            elif self.program[pos] == '\\':
                depth -= 1
            pos += 1
        return pos - 1 if depth == 0 else -1

    # Jump to a specific ' command based on current cell value
    def goto_command(self):
        # Check if directly following /
        if self.instruction_pointer > 0 and self.program[self.instruction_pointer - 1] == '/':
            self.instruction_pointer += 1
            return
        
        current_value = self.get_cell_value(self.data_pointer)
        
        if len(self.loop_scopes) == 0:
            # No loop scope, just advance
            self.instruction_pointer += 1
            return
        
        # Get deepest (innermost) loop scope
        loop_start, loop_end = self.loop_scopes[-1]
        
        if current_value == 0:
            # Jump to after the \
            self.instruction_pointer = loop_end + 1
            return
        
        # Find all ' commands within this loop range (excluding nested loops)
        jump_positions = []
        depth = 0
        for i in range(loop_start + 1, loop_end):
            if self.program[i] == '/':
                depth += 1
            elif self.program[i] == '\\':
                depth -= 1
            elif self.program[i] == "'" and depth == 0:
                # Only count ' at the current nesting level
                jump_positions.append(i)
        
        # Jump to the (current_value)th ' command (1-based)
        if 1 <= current_value <= len(jump_positions):
            self.instruction_pointer = jump_positions[current_value - 1]
        else:
            # Value out of range, just advance
            self.instruction_pointer += 1
    
    # Perform logical not on current cell
    def logical_not(self):
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            if self.tape[self.data_pointer] == 0:
                self.tape[self.data_pointer] = 1
            else:
                self.tape[self.data_pointer] = 0
    
    # Zero current cell and add its value to all other cells 
    def distribute_value(self):
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            value = self.tape[self.data_pointer]
            self.tape[self.data_pointer] = 0
            
            for i in range(len(self.tape)):
                if i != self.data_pointer and i not in self.readonly_cells:
                    self.tape[i] += value

    # Delete current cell
    def delete_cell(self):
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            del self.tape[self.data_pointer]
            
            # Adjust read-only indices
            new_readonly = set()
            for i in self.readonly_cells:
                if i > self.data_pointer:
                    new_readonly.add(i - 1)
                elif i < self.data_pointer:
                    new_readonly.add(i)
                # If i == self.data_pointer, it's deleted
            self.readonly_cells = new_readonly
            
            # Adjust pointer
            if self.data_pointer >= len(self.tape) and len(self.tape) > 0:
                self.data_pointer = len(self.tape) - 1
            elif len(self.tape) == 0:
                self.data_pointer = 0
    
    # Number from stdin
    def input_number(self):
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            try:
                value = int(input())
                self.tape[self.data_pointer] = max(0, value)  # Keep positive
            except (ValueError, EOFError):
                pass
    
    # Unicode character from stdin
    def input_unicode(self):
        if self.is_on_tape() and self.data_pointer not in self.readonly_cells:
            try:
                char = input()
                if len(char) > 0:
                    self.tape[self.data_pointer] = ord(char[0])
            except EOFError:
                pass
    
    # Output the current cell as a number
    def output_number(self):
        if self.is_on_tape():
            print(self.tape[self.data_pointer], end='')
    
    # Output the current cell as a unicode character
    def output_unicode(self):
        if self.is_on_tape():
            try:
                print(chr(self.tape[self.data_pointer]), end='')
            except (ValueError, OverflowError):
                pass
    
    # Toggle read-only status of current cell
    def toggle_readonly(self):
        if self.is_on_tape():
            if self.data_pointer in self.readonly_cells:
                self.readonly_cells.discard(self.data_pointer)
            else:
                self.readonly_cells.add(self.data_pointer)

    # Create functions 
    def define_function(self, name, code):
        self.functions[name] = code

    # Call functions
    def call_function(self, name):
        if name not in self.functions:
            return
            
        # Save state
        saved_program = self.program
        saved_ip = self.instruction_pointer
        saved_scopes = self.loop_scopes[:]
        
        # Execute function
        self.program = self.functions[name]
        self.instruction_pointer = 0
        self.loop_scopes = []
        
        while self.instruction_pointer < len(self.program):
            if not self.execute_instruction():
                break
        
        # Restore state (but keep tape/pointer changes!)
        self.program = saved_program
        self.instruction_pointer = saved_ip
        self.loop_scopes = saved_scopes
    
    # Import functions from another file
    def import_functions(self, filename):
        try:
            with open(filename, 'r') as f:
                content = f.read()
                # Find all {@name@code@} patterns
                pattern = r'\{@([^@]+)@([^@]*)@\}'
                for match in re.finditer(pattern, content):
                    name, code = match.groups()
                    self.functions[name] = code
        except FileNotFoundError:
            print(f"Error: Could not import from {filename}", file=sys.stderr)
        except Exception as e:
            print(f"Error importing from {filename}: {e}", file=sys.stderr)

    # Execute shell commands 
    def execute_shell_command(self, command):
        """Execute shell command with cell value substitutions"""
        # Replace \cell(N)\ with numeric value
        def replace_cell(match):
            pos = int(match.group(1))
            return str(self.get_cell_value(pos))
        
        # Replace \ccell(N)\ with character
        def replace_ccell(match):
            pos = int(match.group(1))
            val = self.get_cell_value(pos)
            try:
                return chr(val)
            except (ValueError, OverflowError):
                return "?"
        
        command = re.sub(r'\\cell\((\d+)\)\\', replace_cell, command)
        command = re.sub(r'\\ccell\((\d+)\)\\', replace_ccell, command)
        
        os.system(command)

    # Comments 
    def skip_comment(self, start_char, end_char):
        depth = 1
        pos = self.instruction_pointer + 1
        while pos < len(self.program) and depth > 0:
            if self.program[pos] == '[':
                depth += 1
            elif self.program[pos] == ']':
                depth -= 1
            pos += 1
        return pos
    
    # Execute a single instruction 
    def execute_instruction(self):
        if self.instruction_pointer >= len(self.program):
            return False
        
        char = self.program[self.instruction_pointer]
        
        # Handle comments: [@...@] and [$...$]
        if char == '[':
            end_pos = self.skip_comment('[', ']')
            self.instruction_pointer = end_pos
            self.previous_was_right = False
            return True
        
        # Handle function definition: {@name@code@}
        if char == '{':
            if (self.instruction_pointer + 1 < len(self.program) and 
                self.program[self.instruction_pointer + 1] == '@'):
                # Find function name
                name_start = self.instruction_pointer + 2
                name_end = self.program.find('@', name_start)
                if name_end != -1:
                    name = self.program[name_start:name_end]
                    # Find function code
                    code_start = name_end + 1
                    code_end = self.program.find('@', code_start)
                    if code_end != -1:
                        code = self.program[code_start:code_end]
                        self.define_function(name, code)
                        # Skip past the closing }
                        self.instruction_pointer = code_end + 2
                        self.previous_was_right = False
                        return True
            self.instruction_pointer += 1
            return True

        # Handle function calls, imports, shell commands: =@name=, =$file=, =$$cmd=
        if char == '=':
            if self.instruction_pointer + 1 < len(self.program):
                next_char = self.program[self.instruction_pointer + 1]
                
                if next_char == '@':
                    # Function call: =@name=
                    name_start = self.instruction_pointer + 2
                    name_end = self.program.find('=', name_start)
                    if name_end != -1:
                        name = self.program[name_start:name_end]
                        self.call_function(name)
                        self.instruction_pointer = name_end + 1
                        self.previous_was_right = False
                        return True
                        
                elif next_char == '$':
                    if (self.instruction_pointer + 2 < len(self.program) and
                        self.program[self.instruction_pointer + 2] == '$'):
                        # Shell command: =$$cmd=
                        cmd_start = self.instruction_pointer + 3
                        cmd_end = self.program.find('=', cmd_start)
                        if cmd_end != -1:
                            command = self.program[cmd_start:cmd_end]
                            self.execute_shell_command(command)
                            self.instruction_pointer = cmd_end + 1
                            self.previous_was_right = False
                            return True
                    else:
                        # Import: =$file=
                        file_start = self.instruction_pointer + 2
                        file_end = self.program.find('=', file_start)
                        if file_end != -1:
                            filename = self.program[file_start:file_end]
                            self.import_functions(filename)
                            self.instruction_pointer = file_end + 1
                            self.previous_was_right = False
                            return True
            
            self.instruction_pointer += 1
            self.previous_was_right = False
            return True

        # Main instruction switch
        if char == '>':
            self.move_data_pointer_right()
            self.previous_was_right = True
            
        elif char == '<':
            self.move_data_pointer_left()
            self.previous_was_right = False
            
        elif char == '^':
            self.increment_cell()
            self.previous_was_right = False
            
        elif char == 'v':
            self.decrement_cell()
            self.previous_was_right = False
            
        elif char == '"':
            if self.previous_was_right:
                self.insert_cell_command()
            else:
                print("Error: \" must be preceded by >", file=sys.stderr)
            self.previous_was_right = False
            
        elif char == "'":
            self.goto_command()
            self.previous_was_right = False
            return True  # goto_command handles instruction_pointer
            
        elif char == '/':
            # Start of loop scope - find matching \
            end_pos = self.find_matching_backslash(self.instruction_pointer)
            if end_pos != -1:
                self.loop_scopes.append((self.instruction_pointer, end_pos))
            self.previous_was_right = False
            
        elif char == '\\':
            # End of loop scope
            if self.loop_scopes:
                self.loop_scopes.pop()
            self.previous_was_right = False
            
        elif char == '!':
            self.logical_not()
            self.previous_was_right = False
            
        elif char == '&':
            self.distribute_value()
            self.previous_was_right = False
            
        elif char == ';':
            # No-op for computer
            self.previous_was_right = False
            
        elif char == '?':
            # No-op for computer
            self.previous_was_right = False
            
        elif char == ':':
            self.delete_cell()
            self.previous_was_right = False
            
        elif char == '~':
            self.input_number()
            self.previous_was_right = False
            
        elif char == '`':
            self.input_unicode()
            self.previous_was_right = False
            
        elif char == '_':
            self.output_number()
            self.previous_was_right = False
            
        elif char == '-':
            self.output_unicode()
            self.previous_was_right = False
            
        elif char == '%':
            self.toggle_readonly()
            self.previous_was_right = False
            
        elif char == '.':
            # Reserved - no-op
            self.previous_was_right = False
            
        else:
            # Unknown character - skip (allows whitespace, etc.)
            self.previous_was_right = False
        
        self.instruction_pointer += 1
        return True
    
    def run(self, program):
        self.program = program
        self.instruction_pointer = 0
        self.previous_was_right = False
        self.tape = []
        self.data_pointer = 0
        self.readonly_cells = set()
        self.loop_scopes = []
        
        while self.instruction_pointer < len(self.program):
            if not self.execute_instruction():
                break
        
        # Print newline at end if we output anything
        print()
    
    def run_file(self, filename):
        try:
            with open(filename, 'r') as f:
                program = f.read()
                self.run(program)
        except FileNotFoundError:
            print(f"Error: File '{filename}' not found", file=sys.stderr)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)

def main():
    if len(sys.argv) < 2:
        print("OATMEAL Interpreter")
        print("Usage: python oatmeal.py <program.oat>")
        print("       python oatmeal.py -e '<code>'")
        return
    
    interpreter = OATMEALInterpreter()
    
    if sys.argv[1] == '-e' and len(sys.argv) > 2:
        # Execute code directly from command line
        interpreter.run(sys.argv[2])
    else:
        filename = sys.argv[1]
        interpreter.run_file(filename)


if __name__ == "__main__":
    main()