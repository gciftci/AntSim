import numpy
import random
import pygame
from math import pi, sin, cos, atan2, radians, degrees
import time
# Constant
WIDTH, HEIGHT = 800, 600
FULLSCREEN = True
VSYNC = True            # limit frame rate to refresh rate
FPS = 60
SHOWFPS = True
ANTS = 200
PRATIO = 4              # Pixel Size for Pheromone grid, 5 is best
DECAY_RATE_FOOD = 0.2   # green
DECAY_RATE_NEST = 0.2
ANT_SCALE = 1
LIFE_TIME = 30

class CaveGenerator:
    def __init__(self, width, height, seed=None, fill_probability=1, iterations=5):
        self.width = width
        self.height = height
        self.fill_probability = fill_probability
        self.iterations = iterations
        random.seed(seed)
        
    def generate_cave(self):
        cave = [[random.choice([0, 1]) if random.random() < self.fill_probability else 0 for _ in range(self.width)] for _ in range(self.height)]
        
        for _ in range(self.iterations):
            cave = self.smooth_cave(cave)
        
        return cave

    def smooth_cave(self, cave):
        new_cave = [[0 for _ in range(self.width)] for _ in range(self.height)]
        
        for y in range(self.height):
            for x in range(self.width):
                walls = self.count_walls(x, y, cave)
                if walls > 4:
                    new_cave[y][x] = 1
                elif walls < 4:
                    new_cave[y][x] = 0
                else:
                    new_cave[y][x] = cave[y][x]

        return new_cave

    def count_walls(self, x, y, cave):
        count = 0
        for i in range(-1, 2):
            for j in range(-1, 2):
                neighbor_x, neighbor_y = x + i, y + j
                if i == 0 and j == 0:
                    continue
                if 0 <= neighbor_x < self.width and 0 <= neighbor_y < self.height:
                    count += cave[neighbor_y][neighbor_x]
                else:
                    count += 1

        return count


# Ant class
class Ant(pygame.sprite.Sprite):
    def __init__(self, drawSurf, nest, pheroLayer):
        super().__init__()
        self.has_food = False
        self.start_time  = time.time()
        self.life_time = LIFE_TIME
        self.birth_time = self.start_time
        
        self.drawSurf = drawSurf
        self.curW, self.curH = self.drawSurf.get_size()
        self.pgSize = (int(self.curW/PRATIO), int(self.curH/PRATIO))
        self.isMyTrail = numpy.full(self.pgSize, False)
        self.phero = pheroLayer
        self.nest = nest
        self.image = pygame.Surface((12, 21)).convert()
        self.image.set_colorkey(0)
        cBrown = (100,42,42)
        # Draw Ant
        pygame.draw.aaline(self.image, cBrown, [0*ANT_SCALE, 5*ANT_SCALE], [11*ANT_SCALE, 15*ANT_SCALE])
        pygame.draw.aaline(self.image, cBrown, [0*ANT_SCALE, 15*ANT_SCALE], [11*ANT_SCALE, 5*ANT_SCALE]) # legs
        pygame.draw.aaline(self.image, cBrown, [0*ANT_SCALE, 10*ANT_SCALE], [12*ANT_SCALE, 10*ANT_SCALE])
        pygame.draw.aaline(self.image, cBrown, [2*ANT_SCALE, 0*ANT_SCALE], [4*ANT_SCALE, 3*ANT_SCALE]) # antena l
        pygame.draw.aaline(self.image, cBrown, [9*ANT_SCALE, 0*ANT_SCALE], [7*ANT_SCALE, 3*ANT_SCALE]) # antena r
        pygame.draw.ellipse(self.image, cBrown, [3*ANT_SCALE, 2*ANT_SCALE, 6*ANT_SCALE, 6*ANT_SCALE]) # head
        pygame.draw.ellipse(self.image, cBrown, [4*ANT_SCALE, 6*ANT_SCALE, 4*ANT_SCALE, 9*ANT_SCALE]) # body
        pygame.draw.ellipse(self.image, cBrown, [3*ANT_SCALE, 13*ANT_SCALE, 6*ANT_SCALE, 8*ANT_SCALE]) # rear
        # save drawing for later
        self.orig_img = pygame.transform.rotate(self.image.copy(), -90)
        self.rect = self.image.get_rect(center=self.nest)
        self.ang = random.randint(0, 360)
        self.desireDir = pygame.Vector2(cos(radians(self.ang)),sin(radians(self.ang)))
        self.pos = pygame.Vector2(self.rect.center)
        self.vel = pygame.Vector2(0,0)
        self.last_sdp = (nest[0]/10/2,nest[1]/10/2)
        self.mode = 0
        
    def update(self, dt):  # behavior  # sourcery skip: low-code-quality
        mid_result = left_result = right_result = [0,0,0]
        mid_GA_result = left_GA_result = right_GA_result = [0,0,0]
        randAng = random.randint(0,360)
        accel = pygame.Vector2(0,0)
        foodColor = (20,150,2)  # color of food to look for
        wandrStr = .06  # how random they walk around
        maxSpeed = 20  # 10-12 seems ok
        steerStr = 4  # 3 or 4, dono
        scaledown_pos = (int(self.pos.x/PRATIO), int(self.pos.y/PRATIO))
        mid_sens = Vec2.vint(self.pos + pygame.Vector2(20, 0).rotate(self.ang))
        left_sens = Vec2.vint(self.pos + pygame.Vector2(18, -8).rotate(self.ang)) # -9
        right_sens = Vec2.vint(self.pos + pygame.Vector2(18, 8).rotate(self.ang)) # 9
        print(time.time()-self.start_time, self.life_time)
        if time.time() - self.start_time > self.life_time:
            self.kill()
        if self.drawSurf.get_rect().collidepoint(mid_sens):
            mspos = (mid_sens[0]//PRATIO,mid_sens[1]//PRATIO)
            mid_result = self.phero.img_array[mspos]
            mid_isID = self.isMyTrail[mspos]
            mid_GA_result = self.drawSurf.get_at(mid_sens)[:3]
        if self.drawSurf.get_rect().collidepoint(left_sens):
            left_result, left_isID, left_GA_result = self.sensCheck(left_sens)
        if self.drawSurf.get_rect().collidepoint(right_sens):
            right_result, right_isID, right_GA_result = self.sensCheck(right_sens)

        if self.mode == 0 and self.pos.distance_to(self.nest) > 21:
            self.mode = 1

        elif self.mode == 1:  # Look for food, or trail to food.
            self.has_food = False
            
            setAcolor = (0,0,100)
            if (
                scaledown_pos != self.last_sdp
                and scaledown_pos[0] in range(self.pgSize[0])
                and scaledown_pos[1] in range(self.pgSize[1])
            ):
                self.phero.img_array[scaledown_pos] += setAcolor
                self.isMyTrail[scaledown_pos] = True
                self.last_sdp = scaledown_pos
            if mid_result[1] > max(left_result[1], right_result[1]):
                self.desireDir += pygame.Vector2(1,0).rotate(self.ang).normalize()
                wandrStr = .1
            elif left_result[1] > right_result[1]:
                self.desireDir += pygame.Vector2(1,-2).rotate(self.ang).normalize() #left (0,-1)
                wandrStr = .1
            elif right_result[1] > left_result[1]:
                self.desireDir += pygame.Vector2(1,2).rotate(self.ang).normalize() #right (0, 1)
                wandrStr = .1
            if left_GA_result == foodColor and right_GA_result != foodColor :
                self.desireDir += pygame.Vector2(0,-1).rotate(self.ang).normalize() #left (0,-1)
                wandrStr = .1
            elif right_GA_result == foodColor and left_GA_result != foodColor:
                self.desireDir += pygame.Vector2(0,1).rotate(self.ang).normalize() #right (0, 1)
                wandrStr = .1
            elif mid_GA_result == foodColor: # if food
                self.desireDir = pygame.Vector2(-1,0).rotate(self.ang).normalize() #pygame.Vector2(self.nest - self.pos).normalize()
                #self.lastFood = self.pos + pygame.Vector2(21, 0).rotate(self.ang)
                maxSpeed = 5
                wandrStr = .01
                steerStr = 5
                self.mode = 2

        elif self.mode == 2:  # Once found food, either follow own trail back to nest, or head in nest's general direction.
            self.has_food = True
            setAcolor = (0,80,0)
            if (
                scaledown_pos != self.last_sdp
                and scaledown_pos[0] in range(self.pgSize[0])
                and scaledown_pos[1] in range(self.pgSize[1])
            ):
                self.phero.img_array[scaledown_pos] += setAcolor
                self.last_sdp = scaledown_pos
            if self.pos.distance_to(self.nest) < 24:
                print("mode2")
                self.has_food = False
                self.start_time = time.time()
                #self.desireDir = pygame.Vector2(self.lastFood - self.pos).normalize()
                self.desireDir = pygame.Vector2(-1,0).rotate(self.ang).normalize()
                self.isMyTrail[:] = False #np.full(self.pgSize, False)
                maxSpeed = 5
                wandrStr = .01
                steerStr = 5
                self.mode = 1
            elif mid_result[2] > max(left_result[2], right_result[2]) and mid_isID: #and mid_result[:2] == (0,0):
                self.desireDir += pygame.Vector2(1,0).rotate(self.ang).normalize()
                wandrStr = .1
            elif left_result[2] > right_result[2] and left_isID: #and left_result[:2] == (0,0):
                self.desireDir += pygame.Vector2(1,-2).rotate(self.ang).normalize() #left (0,-1)
                wandrStr = .1
            elif right_result[2] > left_result[2] and right_isID: #and right_result[:2] == (0,0):
                self.desireDir += pygame.Vector2(1,2).rotate(self.ang).normalize() #right (0, 1)
                wandrStr = .1
            else:  # maybe first add ELSE FOLLOW OTHER TRAILS?
                
                self.desireDir += pygame.Vector2(self.nest - self.pos).normalize() * .08
                wandrStr = .1   #pygame.Vector2(self.desireDir + (1,0)).rotate(pygame.math.Vector2.as_polar(self.nest - self.pos)[1])

        wallColor = (50,50,50)  # avoid walls of this color
        if left_GA_result == wallColor:
            self.desireDir += pygame.Vector2(0,2).rotate(self.ang) #.normalize()
            wandrStr = .1
            steerStr = 7
        elif right_GA_result == wallColor:
            self.desireDir += pygame.Vector2(0,-2).rotate(self.ang) #.normalize()
            wandrStr = .1
            steerStr = 7
        elif mid_GA_result == wallColor:
            self.desireDir = pygame.Vector2(-2,0).rotate(self.ang) #.normalize()
            maxSpeed = 4
            wandrStr = .1
            steerStr = 7

        # Avoid edges
        screen_rect = self.drawSurf.get_rect()
        if not screen_rect.collidepoint(left_sens) and screen_rect.collidepoint(right_sens):
            self.desireDir += pygame.Vector2(0,1).rotate(self.ang) #.normalize()
            wandrStr = .01
            steerStr = 5
        elif not screen_rect.collidepoint(right_sens) and screen_rect.collidepoint(left_sens):
            self.desireDir += pygame.Vector2(0,-1).rotate(self.ang) #.normalize()
            wandrStr = .01
            steerStr = 5
        elif not screen_rect.collidepoint(Vec2.vint(self.pos + pygame.Vector2(21, 0).rotate(self.ang))):
            self.desireDir += pygame.Vector2(-1,0).rotate(self.ang) #.normalize()
            maxSpeed = 5
            wandrStr = .01
            steerStr = 5

        randDir = pygame.Vector2(cos(radians(randAng)),sin(radians(randAng)))
        self.desireDir = pygame.Vector2(self.desireDir + randDir * wandrStr).normalize()
        dzVel = self.desireDir * maxSpeed
        dzStrFrc = (dzVel - self.vel) * steerStr
        accel = dzStrFrc if pygame.Vector2(dzStrFrc).magnitude() <= steerStr else pygame.Vector2(dzStrFrc.normalize() * steerStr)
        velo = self.vel + accel * dt
        self.vel = velo if pygame.Vector2(velo).magnitude() <= maxSpeed else pygame.Vector2(velo.normalize() * maxSpeed)
        self.pos += self.vel * dt
        self.ang = degrees(atan2(self.vel[1],self.vel[0]))
        # adjusts angle of img to match heading
        self.image = pygame.transform.rotate(self.orig_img, -self.ang)
        self.rect = self.image.get_rect(center=self.rect.center)  # recentering fix
        # actually update position
        self.rect.center = self.pos

    def sensCheck(self, pos): #, pos2): # checks given points in Array, IDs, and pixels on screen.
        sdpos = (int(pos[0]/PRATIO) -1,int(pos[1]/PRATIO) -1)
        array_r = self.phero.img_array[sdpos]
        ga_r = self.drawSurf.get_at(pos)[:3]
        return array_r, self.isMyTrail[sdpos], ga_r

class PheroGrid():
    def __init__(self, bigSize):
        self.surfSize = (int(bigSize[0]/PRATIO), int(bigSize[1]/PRATIO))
        self.image = pygame.Surface(self.surfSize).convert()
        self.img_array = numpy.array(pygame.surfarray.array3d(self.image),dtype=float)#.astype(numpy.float64)
        
    def update(self, dt):
        decay_food = DECAY_RATE_FOOD * (60/FPS) * ((dt/10) * FPS)
        decay_nest = DECAY_RATE_NEST * (60/FPS) * ((dt/10) * FPS)
       # self.img_array -= DECAY_RATE * (60/FPS) * ((dt/10) * FPS) #[self.img_array > 0] # dt might not need FPS parts
        self.img_array[..., 0] -= decay_nest
        self.img_array[..., 1] -= decay_food
        self.img_array[..., 2] -= decay_nest
        self.img_array = self.img_array.clip(0,255)
        #self.pixelID[ (self.img_array == (0, 0, 0))[:, :, 0] ] = 0  # not sure if works, or worth it
        #indices = (img_array == (0, 0, 0))[:, :, 0] # alternative in 2 lines
        #pixelID[indices] = 0
        #self.img_array[self.img_array < 1] = 0  # ensure no leftover floats <1
        #self.img_array[self.img_array > 255] = 255  # ensures nothing over 255, replaced by clip
        pygame.surfarray.blit_array(self.image, self.img_array)
        return self.image
        
class Food(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.pos = pos
        self.image = pygame.Surface((16, 16))
        self.image.fill(0)
        self.image.set_colorkey(0)
        pygame.draw.circle(self.image, [20,150,2], [8, 8], 4)
        self.rect = self.image.get_rect(center=pos)
    def pickup(self):
        self.kill()

class Vec2():
	def __init__(self, x=0, y=0):
		self.x = x
		self.y = y
	def vint(self):
		return (int(self.x), int(self.y))    

# Main Func
def start_sim():
    # Initialize PyGame
    pygame.init()
    pygame.display.set_caption("Ant Pheromone Simulation")
    # setup fullscreen or window mode
    if FULLSCREEN:  #screen = pygame.display.set_mode((0,0), pygame.FULLSCREEN)
        currentRez = (pygame.display.Info().current_w, pygame.display.Info().current_h)
        screen = pygame.display.set_mode(currentRez, pygame.SCALED | pygame.NOFRAME | pygame.FULLSCREEN, vsync=VSYNC)
    else: 
        screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.SCALED, vsync=VSYNC)
    cur_w, cur_h = screen.get_size()
    screenSize = (cur_w, cur_h)
    nest = (cur_w/3, cur_h/2)

    workers = pygame.sprite.Group()
    pheroLayer = PheroGrid(screenSize)

    for _ in range(ANTS):
        workers.add(Ant(screen, nest, pheroLayer))

    foodList = []
    foods = pygame.sprite.Group()
    font = pygame.font.Font(None, 30)
    clock = pygame.time.Clock()
    fpsChecker = 0
    width, height = 50, 50
    tile_size = 10
    cave_generator = CaveGenerator(width, height, seed=42)
    cave = cave_generator.generate_cave()
    def draw_cave_and_ants(cave):
        for y in range(height):
            for x in range(width):
                color = (0, 0, 0) if cave[y][x] == 1 else (255, 255, 255)
                pygame.draw.rect(screen, color, (x * tile_size, y * tile_size, tile_size, tile_size))

    # main loop
    while True:
        for e in pygame.event.get():
            if e.type == pygame.QUIT or e.type == pygame.KEYDOWN and e.key == pygame.K_ESCAPE:
                return
            elif e.type == pygame.MOUSEBUTTONDOWN:
                mousepos = pygame.mouse.get_pos()
                if e.button == 1:
                    foodBits = 200
                    fRadius = 50
                    for i in range(foodBits):
                        dist = pow(i / (foodBits - 1.0), 0.5) * fRadius
                        angle = 2 * pi * 0.618033 * i
                        fx = mousepos[0] + dist * cos(angle)
                        fy = mousepos[1] + dist * sin(angle)
                        foods.add(Food((fx,fy)))
                    foodList.extend(foods.sprites())
                elif e.button == 3:
                    for fbit in foodList:
                        if pygame.Vector2(mousepos).distance_to(fbit.rect.center) < fRadius+5:
                            fbit.pickup()
                    foodList = foods.sprites()
        draw_cave_and_ants(cave)
        dt = clock.tick(FPS) / 100
        pheroImg = pheroLayer.update(dt)
        pheroLayer.img_array[170:182,0:80] = (50,50,50)  # wall

        workers.update(dt)

        rescaled_img = pygame.transform.scale(pheroImg, (cur_w, cur_h))
        pygame.Surface.blit(screen, rescaled_img, (0,0))

        foods.draw(screen)

        pygame.draw.circle(screen, [40,10,10], (nest[0],nest[1]+6), 6, 3)
        pygame.draw.circle(screen, [50,20,20], (nest[0],nest[1]+4), 9, 4)
        pygame.draw.circle(screen, [60,30,30], (nest[0],nest[1]+2), 12, 4)
        pygame.draw.circle(screen, [70,40,40], nest, 16, 5)

        workers.draw(screen)

        if SHOWFPS : screen.blit(font.render(str(int(clock.get_fps())), True, [0,200,0]), (8, 8))

        pygame.display.update()
