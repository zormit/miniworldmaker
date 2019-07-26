import os
from collections import defaultdict
from collections import deque
from typing import Union

import pygame
from miniworldmaker.boards import background
from miniworldmaker.boards import board_position
from miniworldmaker.boards import board_rect
from miniworldmaker.containers import container
from miniworldmaker.physics import physics as physicsengine
from miniworldmaker.tokens import token as tkn
from miniworldmaker.tools import db_manager
from miniworldmaker.windows import miniworldwindow as window


class Board(container.Container):
    """Base Class for Boards

    Args:
        columns: columns of new board (default: 40)
        rows: rows of new board (default:40)

    """

    registered_event_handlers_for_tokens = defaultdict(defaultdict)
    registered_collision_handlers_for_tokens = defaultdict(list)

    def __init__(self,
                 columns: int = 40,
                 rows: int = 40,
                 tile_size=1,
                 tile_margin=0,
                 ):

        super().__init__()
        pygame.init()
        # public
        self.registered_events = {"all"}
        self.is_running = True
        if not hasattr(self, "default_token_speed"):
            self.default_token_speed = 3  #: default speed for tokens
        self.sound_effects = {}
        self.physics_accuracy = 1
        self.physics_property = physicsengine.PhysicsProperty
        # private
        if not hasattr(self, "_fps"):
            self._fps = 60  # property speed
        self._tokens = pygame.sprite.LayeredDirty()
        self._key_pressed = False
        self._animated = False
        self._grid = []
        self._orientation = 0
        self._repaint_all = False
        if type(columns) != int or type(rows) != int:
            raise TypeError("ERROR: columns and rows should be int values but types are",
                            str(type(columns)), "and", str(type(rows)))
        self._columns, self._rows, self._tile_size, self._tile_margin = columns, rows, tile_size, tile_margin
        self._grid = []
        for row in range(self.rows):
            self._grid.append([])
            for column in range(self.columns):
                self._grid[row].append(0)

        self.background = background.Background(self)
        self.backgrounds = [self.background]
        self._image = pygame.Surface((1, 1))
        self.surface = pygame.Surface((1, 1))
        # protected
        self.frame = 0
        self._tick = 0
        self.clock = pygame.time.Clock()
        self.__last_update = pygame.time.get_ticks()
        # Init graphics
        self.dirty = 1  # Information: A board is always dirty
        self._window = window.MiniWorldWindow("MiniWorldMaker")
        self._window.add_container(self, "top_left")
        window.MiniWorldWindow.board = self
        self.registered_event_handlers = dict()
        self.tokens_with_eventhandler = defaultdict(list)
        self.tokens_with_collisionhandler = defaultdict(list)
        self.setup_tokens = deque()
        self.dirty = 1
        self._repaint_all = 1
        if hasattr(self, "on_setup"):
            self.on_setup()
        if hasattr(self, "setup"):
            self.setup()


    @classmethod
    def from_db(cls, file):
        """
        Loads a sqlite db file.

        Args:
            file:

        Returns:

        """
        db = db_manager.DBManager(file)
        data = db.select_single_row("SELECT rows, columns, tile_size, tile_margin, board_class FROM Board")
        board = cls()
        board.rows = data[0]
        board.columns = data[1]
        board._tile_size = data[2]
        board._tile_margin = data[3]
        data = db.select_all_rows("SELECT token_id, column, row, token_class FROM token")

        if data:
            for tokens in data:
                token_class_name = tokens[3]
                token_class = tkn.Token
                class_list = tkn.Token.all_subclasses()
                for cls_obj in class_list:
                    if cls_obj.__name__ == token_class_name:
                        token_class = cls_obj
                token_class(position=(tokens[1], tokens[2]))  # Create token
        board.window.send_event_to_containers("Loaded from db", board)
        return board

    @classmethod
    def all_subclasses(cls):
        def rec_all_subs(base_cls) -> set:
            return set(base_cls.__subclasses__()).union(
                [s for c in base_cls.__subclasses__() for s in rec_all_subs(c)])
        return rec_all_subs(cls)

    def __str__(self):
        return "{0} with {1} columns and {2} rows"\
            .format(self.__class__.__name__, self.columns, self.rows)

    def _act_all(self):
        self._call_all_token_setups()
        for token in self.tokens_with_eventhandler["act"]:
            if not token.setup_completed:
                self._call_all_token_setups()
            token.act()
        if "act" in self.registered_event_handlers:
            if hasattr(self, "act"):
                self.act()

    def _call_all_token_setups(self):
        while self.setup_tokens:
            token = self.setup_tokens.popleft()
            if not token.setup_completed:
                if not token.setup_completed:
                    print("call token setups", self.registered_event_handlers_for_tokens)
                    if "setup" in self.registered_event_handlers_for_tokens[token.__class__]:
                        self.registered_event_handlers_for_tokens[token.__class__]["setup"](token, **token.kwargs)
                        print("setup called")
                        token.setup_completed = True
                token.dirty = 1
            token.setup_completed = True

    @property
    def container_width(self) -> int:
        """
        Gets the width of the container

        Returns:
            The width of the container (in pixels on a PixelGrid; in Tiles on a TiledGrid)

        """
        if self.dirty:
            self._container_width = self.columns * self.tile_size + (self.columns + 1) * self.tile_margin
        return self._container_width

    @property
    def container_height(self) -> int:
        """
        Gets the height of the container

        Returns:
            The height of the container (in pixels on a PixelGrid; in Tiles on a TiledGrid)

        """
        if self.dirty:
            self._container_height = self.rows * self.tile_size + (self.rows + 1) * self.tile_margin
        return self._container_height

    @property
    def fps(self) -> int:
        """
        The world speed. The world speed is counted in fps (frames per second).

        """
        return self._fps

    @fps.setter
    def fps(self, value: int):
        self._fps = value

    @property
    def width(self) -> int:
        """
        See container_width
        """
        return self.container_width

    @property
    def height(self) -> int:
        """
        See container_height
        """
        return self.container_height

    @property
    def window(self) -> window.MiniWorldWindow:
        """
        Gets the parent window

        Returns:
            The window

        """
        return self._window

    @property
    def rows(self) -> int:
        """
        The number of rows
        """
        return self._rows

    @rows.setter
    def rows(self, value):
        self._rows = value
        self.dirty = 1
        self.window.dirty = 1
        self._repaint_all = 1

    @property
    def columns(self) -> int:
        """
        The number of columns
        """
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = value
        self.window.dirty = 1
        self._repaint_all = 1
        
    @property
    def tile_size(self) -> int:
        """
        The number of columns
        """
        return self._tile_size

    @tile_size.setter
    def tile_size(self, value):
        self._tile_size = value
        self.window.dirty = 1
        self._repaint_all = 1

    @property
    def tile_margin(self) -> int:
        """
        The number of columns
        """
        return self._tile_margin

    @tile_margin.setter
    def tile_margin(self, value):
        self._tile_margin = value
        self.window.dirty = 1
        self._repaint_all = 1

    @property
    def tokens(self) -> pygame.sprite.LayeredDirty:
        """
        A list of all tokens registered to the grid.
        """
        return self._tokens

    @property
    def class_name(self) -> str:
        return self.__class__.__name__

    def add_background(self, path: str) -> background.Background:
        """
        Adds a new background to the board

        Args:
            path: The path to the first image of the background

        Returns:

        """
        new_background = background.Background(self)
        new_background.add_image(path)
        new_background.orientation = self.background.orientation
        self.backgrounds.append(new_background)
        return new_background

    def add_image(self, path: str) -> int:
        """
        Adds image to current background.
        If no background is created yet, a new background will be created with this image.

        Args:
            path: The path to the image as relative path

        Returns:
            The index of the image.

        Examples:
            >>> class MyBoard(Board):
            >>>     def __init__(self):
            >>>         super().__init__(columns=400, rows=200)
            >>>         self.add_image(path="images/stone.jpg")
            Creates Board with file stone.jpg in folder images as background

        """
        try:
            image = self.background.add_image(path)
        except FileExistsError:
            raise FileExistsError("File '{0}' does not exist. Check your path to the image.".format(path))
        return image

    def add_to_board(self, token, position: board_position.BoardPosition):
        """
        Adds an actor to the board.
        Is called in __init__-Method if position is set.

        Args:
            board: The board, the actor should be added
            position: The position on the board where the actor should be added.
        """
        self.tokens.add(token)
        token.position = position
        token.costume.changed_all()
        token.dirty = 1
        if token.init != 1:
            raise UnboundLocalError("super().__init__() was not called")
        if token.speed == 0:
            token.speed = self.default_token_speed
        self.setup_tokens.append(token)
        self.update_event_handling()

    def blit_surface_to_window_surface(self):
        self._window.window_surface.blit(self.surface, self.rect)

    def get_colors_at_position(self, position: Union[tuple, board_position.BoardPosition]):
        if type(position) == tuple:
            position = board_position.BoardPosition(position[0], position[1])
        return position.color()

    def get_colors_at_line(self, line: list):
        """
        Gets all colors in a line. A line is a list of board_positions

        Args:
            line: the line

        Returns: A list of all colors found at the line

        """
        colors = []
        for pos in line:
            if type(pos) == tuple:
                pos = board_position.BoardPosition.from_tuple(pos)
            color_at_pos = pos.color()
            if color_at_pos not in colors:
                colors.append(color_at_pos)
        return colors

    def get_color_at_rect(self, rect: board_rect.BoardRect, directions=None) -> list:
        return rect.colors()

    def get_tokens_by_pixel(self, pixel: tuple) -> list:
        """Gets all tokens by Pixel.

        Args:
            pixel: the pixel-coordinates

        Returns:
            A list of tokens

        Examples:
            >>> position = board.get_mouse_position()
            >>> tokens = board.get_tokens_by_pixel(position)

        """
        token = []
        for actor in self.tokens:
            if actor.rect.collidepoint(pixel):
                token.append(actor)
        return token

    def get_tokens_at_rect(self, rect: pygame.Rect, singleitem=False, exclude=None, token_type=None) -> Union[
        tkn.Token, list]:
        """
        Gets all Tokens which are colliding with a given rect.

        Args:
            rect: The rect
            singleitem: Should the method return a single token (faster) or all tokens at rect (slower)
            exclude: Exclude a token
            token_type: Filter return values by token type

        Returns: A single token or a list of tokens at rect

        """
        pass

    @property
    def image(self) -> pygame.Surface:
        """
        The current displayed image
        """
        self._image = self.background.image
        return self._image

    def remove_tokens_from_rect(self, rect: Union[tuple, pygame.Rect], token=None, exclude=None):
        """Removes all tokens in an area

        Args:
            rect: A rectangle or a tuple (which is automated converted to a rectangle with tile_size
            token: The class of the tokens which should be removed
            exclude: A token which should not be removed e.g. the actor itself

        Returns: all tokens in the area
        """
        if type(rect) == tuple:
            rect = pygame.Rect(rect[0], rect[1], 1, 1)
        tokens = self.get_tokens_at_rect(rect)
        if token is not None:
            tokens = Board.filter_actor_list(tokens, token)
        for token in tokens:
            token.remove()

    def reset(self):
        """Resets the board
        Creates a new board with init-function - recreates all tokens and actors on the board.

        Returns:
            The newly created and reseted board
        """
        board = self.__class__(self.width, self.height)
        board.is_running = False
        board.window.send_event_to_containers("reset", board)
        board.show()
        return board

    def repaint(self):
        if self._repaint_all:
            self.surface = pygame.Surface((self.image.get_width(), self.image.get_height()))
            self.surface.blit(self.image, self.surface.get_rect())
        self.tokens.clear(self.surface, self.image)
        repaint_rects = self.tokens.draw(self.surface)
        self._window.repaint_areas.extend(repaint_rects)
        if self._repaint_all:
            self._window.repaint_areas.append(self.rect)
            self._repaint_all = False

    def show(self, fullscreen=False):
        """
        The method show() should always called at the end of your program.
        It starts the mainloop.

        Examples:
            >>> my_board = Board() # or a subclass of Board
            >>> my_board.show()

        """
        self.background.is_scaled = True
        self.background.size = self.container_width, self.container_height
        image = self.image
        self.window.show(image, full_screen=fullscreen)

    def switch_background(self, index=-1) -> background.Background:
        """Switches the background

        Args:
            index: The index of the new costume. If index=-1, the next costume will be selected

        Returns: The new costume

        """
        if index == -1:
            index = self.backgrounds.index(self.background)
            if index < len(self.backgrounds) - 1:
                index += 1
            else:
                index = 0
        else:
            index = index
        self.background = self.backgrounds[index]
        self.background.dirty = 1
        self.background.changed_all()
        self.background_changed = 1
        self._repaint_all = True
        for token in self.tokens:
            token.dirty = 1
        return self.background

    def update(self):
        # This is the board-mainloop()
        # Called in miniworldwindow.update as ct.update()
        # Event handling is in miniworldwindow and is called before update().
        if self.is_running:
            self._tick = 0
            # Acting for all actors
            self._act_all()
            self.collision_handling()
            # run animations
            for token in self.tokens:
                token.costume.next_image()
            # If there are physic objects, run a physics simulation step
            if physicsengine.PhysicsProperty.count > 0:
                physics_tokens = [token for token in self.tokens if token.physics and token.physics.started]
                for token in physics_tokens:
                    token.physics.update_physics_model()
                steps = self.physics_accuracy
                for x in range(steps):
                    if physicsengine is not None and \
                            physicsengine.PhysicsProperty.space is not None:
                        physicsengine.PhysicsProperty.space.step(1 / (60 * steps))
                for token in physics_tokens:
                    token.physics.update_token_from_physics_model()
        self.frame = self.frame + 1
        self.clock.tick(self.fps)



    def handle_event(self, event, data=None):
        self._call_all_token_setups()
        # calls all registered event handlers of tokens
        tokens = self.tokens_with_eventhandler[event]
        for token in tokens:
            return self.registered_event_handlers_for_tokens[token.__class__][event](token, data)
        tokens = self.tokens_with_eventhandler["get_event"]
        for token in tokens:
            return self.registered_event_handlers_for_tokens[token.__class__]["get_event"](token, event, data)
        # Call events of board
        if event in self.registered_event_handlers.keys():
            # calls registered event handlers of board
            if data is None:
                self.registered_event_handlers[event]()
            else:
                self.registered_event_handlers[event](data)
        self.get_event(event, data)

    def collision_handling(self):
        self._call_all_token_setups()
        # Collisions with other tokens
        for token in self.tokens:
            # registered collision handlers are set in
            for coll_class in self.registered_collision_handlers_for_tokens[token.__class__]:
                if coll_class not in ["borders", "on_board", "not_on_board"]:
                    collision_tokens = token.sensing_tokens(token_type=coll_class, exact=True)
                    ("Colliding with", collision_tokens)
                    if collision_tokens:
                        for colliding_target in collision_tokens:
                            method = getattr(token, 'on_sensing_' + str(coll_class.__name__).lower())
                            if callable(method):
                                method(colliding_target)
                elif coll_class == "borders":
                    borders = token.sensing_borders()
                    if borders:
                        method = getattr(token, 'on_sensing_borders'.lower())
                        if callable(method):
                            print("on_sensing_borders")
                            method(borders)
                elif coll_class == "not_on_board":
                    on_board = token.sensing_on_board()
                    if not on_board:
                        method = getattr(token, 'on_sensing_not_on_board'.lower())
                        if callable(method):
                            print("on_sensing_not_on_board")
                            method()
                elif coll_class == "on_board":
                    on_board = token.sensing_on_board()
                    if on_board:
                        method = getattr(token, 'on_sensing_on_board'.lower())
                        if callable(method):
                            print("on_sensing_on_board")
                            method()

    def save_to_db(self, file):
        """
        Saves the current board an all actors to database.
        The file is stored as db file and can be opened with sqlite.

        Args:
            file: The file as relative location

        Returns:

        """
        if os.path.exists(file):
            os.remove(file)
        db = db_manager.DBManager(file)
        query_actors = """     CREATE TABLE `token` (
                        `token_id`			INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
                        `column`		INTEGER,
                        `row`			INTEGER,
                        `token_class`	TEXT,
                        `parent_class`  TEXT
                        );
                        """
        query_board = """     CREATE TABLE `board` (
                        `tile_size`		INTEGER,
                        `rows`			INTEGER,
                        `columns`		INTEGER,
                        `tile_margin`	INTEGER,
                        `board_class`	TEXT
                        );
                        """
        cur = db.cursor
        cur.execute(query_actors)
        cur.execute(query_board)
        db.commit()
        for token in self.tokens:
            token_dict = {"column": token.position[0],
                          "row": token.position[1],
                          "token_class": token.__class__.__name__}
            db.insert(table="token", row=token_dict)
        board_dict = {"rows": self.rows,
                      "columns": self.columns,
                      "tile_margin": self.tile_margin,
                      "tile_size": self.tile_size,
                      "board_class": self.__class__.__name__}
        db.insert(table="board", row=board_dict)
        db.commit()
        db.close_connection()
        self.window.send_event_to_containers("Saved to db", file)

    def play_sound(self, path: str):
        if path.endswith("mp3"):
            path = path[:-4] + "wav"
        if path in self.sound_effects.keys():
            self.sound_effects[path].play()
        else:
            effect = self.register_sound(path)
            effect.play()

    def play_music(self, path: str):
        """
        plays a music by path

        Args:
            path: The path to the music

        Returns:

        """
        pygame.mixer.music.load(path)
        pygame.mixer.music.play(-1)

    def find_colors(self, rect, color, threshold=(20, 20, 20, 20)):
        return self.background.count_pixels_by_color(rect, color, threshold)

    def get_mouse_position(self) -> Union[board_position.BoardPosition, None]:
        """
        Gets the current mouse_position

        Returns:
            Returns the mouse position if mouse is on board. Returns "None" otherwise

        Examples:
            This example shows you how to use the mouse_position

            >>> def act(self):
            >>>     mouse = self.board.get_mouse_position()
            >>>     if mouse:
            >>>         self.point_towards_position(mouse)

        """
        pos = board_position.BoardPosition.from_pixel(pygame.mouse.get_pos())
        clicked_container = self.window.get_container_by_pixel(pos[0], pos[1])
        if clicked_container == self:
            return pos
        else:
            return None

    def update_event_handling(self):
        self.tokens_with_eventhandler.clear()
        for token in self.tokens:
            for event_handler in self.registered_event_handlers_for_tokens[token.__class__].keys():
                self.tokens_with_eventhandler[event_handler].append(token)

    def is_position_on_board(self, position: board_position.BoardPosition) -> bool:
        """Tests if area or position is on board

        Args:
            position: A rectangle or a position

        Returns:
            true, if area is in grid

        """
        if type(position) == tuple:
            position = board_position.BoardPosition(position[0], position[1])
        if type(position) == board_position.BoardPosition:
            position = position.to_rect()

        top_left_x, top_left_y, right, top = position.topleft[0], \
                                             position.topleft[1], \
                                             position.right, \
                                             position.top
        if top_left_x < 0 or top_left_y < 0 or position.right >= self.width or position.bottom >= self.height:
            return False
        else:
            return True

    def register_sound(self, path) -> pygame.mixer.Sound:
        """
        Registers a sound effect to board-sound effects library
        Args:
            path: The path to sound

        Returns: the sound

        """
        try:
            effect = pygame.mixer.Sound(path)
            self.sound_effects[path] = effect
            return effect
        except pygame.error:
            raise FileExistsError("File '{0}' does not exist. Check your path to the sound.".format(path))

    def register_collision_handlers(self):
        from miniworldmaker.tokens import token
        token_subclasses = token.Token.all_subclasses()
        dict_with_all_token_subclasses = dict()
        for cls in token_subclasses:
            dict_with_all_token_subclasses[cls.__name__] = cls
        for subcls in token_subclasses: # Search subclasses for method names
            method_list = [func for func in dir(subcls) if
                           callable(getattr(subcls, func)) and func.startswith("on_sensing_")]
            for method in method_list:
                on_sensing_target = method[11:]
                class_name = on_sensing_target.capitalize() # check if on_sensing_[class_name] is a existing class
                colliding_class = dict_with_all_token_subclasses.get(class_name, None)
                if colliding_class:
                    self.registered_collision_handlers_for_tokens[subcls].append(colliding_class)
                # Add on_sensing_border handler
                elif on_sensing_target == "borders":
                    self.registered_collision_handlers_for_tokens[subcls].append("borders")
                elif on_sensing_target == "not_on_board":
                    self.registered_collision_handlers_for_tokens[subcls].append("not_on_board")
                elif on_sensing_target == "not_on_board":
                    self.registered_collision_handlers_for_tokens[subcls].append("on_board")

    def register_event_handlers(self):
        """
        Add an event handler for every registered submethod
        Returns:

        """
        # Add handlers for token events
        from miniworldmaker.tokens import token
        token_subclasses = token.Token.all_subclasses()
        for subcls in token_subclasses:
            # Adds the on_key_up, on_mouse... events, if the corresponding method exists
            for event in window.MiniWorldWindow.input_events:
                # Adds Event handler, e.g. method on_key_up for event "key_up"
                handler = getattr(subcls, event, None)
                if handler and callable(handler):
                    self.registered_event_handlers_for_tokens[subcls][event] = handler
                # Adds Event handler on_key_up for event "key up"
                handler = getattr(subcls, "on_" + event, None)
                if callable(handler):
                    self.registered_event_handlers_for_tokens[subcls][event] = handler
            # Adds Event handler get_event for all event, if get_event is callable
            get_event = getattr(subcls, "get_event", None)
            if get_event and callable(get_event):
                self.registered_event_handlers_for_tokens[subcls]["get_event"] = get_event
            # Adds Act-handler
            act = getattr(subcls, "act", None)
            if act and callable(act):
                self.registered_event_handlers_for_tokens[subcls]["act"] = act
            # Add Setup Handler
            setup = getattr(subcls, "setup", None)
            if callable(setup):
                self.registered_event_handlers_for_tokens[subcls]["setup"] = setup
            on_setup = getattr(subcls, "on_setup", None)
            if callable(on_setup):
                self.registered_event_handlers_for_tokens[subcls]["setup"] = on_setup
        # Add handlers for board events
        for event in window.MiniWorldWindow.input_events:
            handler = getattr(self.__class__, event, None)
            if handler and callable(handler):
                self.registered_event_handlers[event] = handler
            # Adds Event handler on_key_up for event "key up"
            handler = getattr(self.__class__, "on_" + event, None)
            if callable(handler):
                self.registered_event_handlers[event] = handler
                # Adds Act-handler
                act = getattr(self, "act", None)
                if act and callable(act):
                    self.registered_event_handlers["act"] = act
        self.update_event_handling()