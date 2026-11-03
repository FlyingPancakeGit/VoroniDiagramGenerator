from settings import *
import random


class Main:
    def __init__(self):
        # setup
        self.display_surface = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.running = True

        pygame.display.set_caption('Voronoi Diagram v1')

        # groups
        self.seed_sprites = pygame.sprite.Group()
        self.triangle_sprites = pygame.sprite.Group()
        self.super_triangle = None
        self.triangles = []

    def get_input(self):
        keys = pygame.key.get_just_pressed()

        if pygame.mouse.get_just_pressed()[0]:
            self.delete_triangles()
            self.create_seed(pygame.mouse.get_pos())
            self.create_triangles()

        if keys[pygame.K_d]:
            self.delete_triangles()
            self.delete_seeds()

        if keys[pygame.K_SPACE]:
            self.delete_triangles()
            self.create_triangles()

        if keys[pygame.K_g]:
            self.delete_triangles()
            self.delete_seeds()
            self.generate_seeds(15)
            self.create_triangles()

    def create_seed(self, pos):
        Seed(self.seed_sprites, pos, (random.randint(100,200), random.randint(100,200), random.randint(100,200)))

    def generate_seeds(self, amount):
        for seed in range(amount):
            pos = (random.randint(10, WINDOW_WIDTH - 10), random.randint(10, WINDOW_HEIGHT - 10))
            Seed(self.seed_sprites, pos, (random.randint(100,200), random.randint(100,200), random.randint(100,200)))

    def delete_seeds(self):
        self.seed_sprites.empty()

    def delete_triangles(self):
        self.triangle_sprites.empty()

    def create_triangles(self):
        # create a triangle that contains all possible seeds within it
        self.super_triangle = Triangle(self.triangle_sprites,
                                       [pygame.math.Vector2(-1000,-1000),
                                        pygame.math.Vector2(WINDOW_WIDTH+1000,-1000),
                                        pygame.math.Vector2(WINDOW_WIDTH/2,WINDOW_HEIGHT+1000)],
                                       (200,200,200))

        for seed in self.seed_sprites:
            invalid_triangles = []

            # for each seed, check if any triangles circumcircles contain that seed. if so, that triangle is invalid.
            for triangle in self.triangle_sprites:
                if triangle.check_point_inside_circumcircle(seed.rect.center):
                    invalid_triangles.append(triangle)

            # remove the invalid triangles, replacing them with ones that have the seed at a vertex
            remaining_edges = []

            # check the edges of all the invalid triangles, to get the edges of the polygonal hole left by their deletion
            for triangle in invalid_triangles:
                for edge in triangle.edges:
                    if edge not in remaining_edges:
                        remaining_edges.append(edge)
                    else:
                        remaining_edges = [remaining_edge for remaining_edge in remaining_edges if remaining_edge != edge]

            # remove all invalid triangles
            for triangle in invalid_triangles:
                triangle.kill()

            # create new valid triangles
            for remaining_edge in remaining_edges:
                vertices = list(remaining_edge)
                vertices.append(seed.rect.center)
                vertices_vectors = [pygame.math.Vector2(v) for v in vertices]
                gb = random.randint(0, 60)
                colour = (random.randint(180, 240), gb, gb)

                Triangle(self.triangle_sprites, vertices_vectors, colour)

        # delete the super triangle, and any edges connected to it
        del_list = []
        for triangle in self.triangle_sprites:
            for vertex in triangle.vertices:
                if vertex in self.super_triangle.vertices:
                    del_list.append(triangle)
                    break

        for triangle in del_list:
            triangle.kill()

        self.super_triangle = None


    def main_loop(self):
        while self.running:
            dt = self.clock.tick() / 1000
            # events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False

            # update
            self.get_input()

            # draw
            self.display_surface.fill(BACKGROUND_COLOUR)
            self.triangle_sprites.draw(self.display_surface)
            self.seed_sprites.draw(self.display_surface)

            pygame.display.update()
        pygame.quit()


class RegionMap(pygame.sprite.Sprite):
    def __init__(self, groups):
        super().__init__(groups)
        self.image = pygame.Surface((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.SRCALPHA)
        self.rect = self.image.get_frect(center=(WINDOW_WIDTH/2, WINDOW_HEIGHT/2))


class Seed(pygame.sprite.Sprite):
    def __init__(self, groups, pos, region_colour):
        # setup
        super().__init__(groups)
        self.image = pygame.Surface((SEED_RADIUS*2, SEED_RADIUS*2), pygame.SRCALPHA)
        pygame.draw.circle(self.image, SEED_COLOUR, (SEED_RADIUS, SEED_RADIUS), SEED_RADIUS)
        self.rect = self.image.get_frect(center=pos)

        # region
        self.region_colour = region_colour


class Triangle(pygame.sprite.Sprite):
    def __init__(self, groups, vertices, colour):
        super().__init__(groups)
        self.image = self.create_image(vertices, colour)
        self.rect = self.image.get_frect(center=self.calculate_image_center(vertices))
        self.vertices = vertices
        self.edges = [{tuple(vertices[0]), tuple(vertices[1])}, {tuple(vertices[1]), tuple(vertices[2])}, {tuple(vertices[2]), tuple(vertices[0])}]
        self.area = self.calculate_triangle_area(vertices)

    def calculate_image_center(self, vertices):
        x_values = [v.x for v in vertices]
        y_values = [v.y for v in vertices]

        width, height = self.calculate_image_dimensions(vertices)

        center = (min(x_values) + width/2, min(y_values) + height/2)

        return center

    def calculate_image_dimensions(self, vertices):
        x_values = [v.x for v in vertices]
        y_values = [v.y for v in vertices]

        width = max(x_values) - min(x_values)
        height = max(y_values) - min(y_values)

        return (width, height)

    def create_image(self, vertices, colour):
        width, height = self.calculate_image_dimensions(vertices)
        center = self.calculate_image_center(vertices)

        image = pygame.Surface((width, height), pygame.SRCALPHA)
        topleft = center - pygame.math.Vector2(width/2, height/2)
        rel_vertices = [v - topleft for v in vertices]
        pygame.draw.polygon(image, colour, rel_vertices)
        return image

    def check_point_inside_circumcircle(self, point):
        projected_vertices = [pygame.math.Vector3(x,y,x**2+y**2) for x, y in self.vertices]

        a = projected_vertices[0]
        b = projected_vertices[1]
        c = projected_vertices[2]
        n = (b-a).cross(c-a)

        # the z-coord at which the given point intersects the plane
        plane_z = lambda p: -(n.x*(p.x-a.x)+n.y*(p.y-a.y))/(n.z)+a.z

        # if the z-coord at which the point collides with the plane is higher than its projected z-coord, then
        # it is within the circumcircle
        if plane_z(pygame.math.Vector2(point)) > (point[0]**2+point[1]**2):
            return True
        else:
            return False

    def calculate_triangle_area(self, vertices):
        return 0.5*(vertices[0][0]*(vertices[1][1]-vertices[2][1])
                   +vertices[1][0]*(vertices[2][1]-vertices[0][1])
                   +vertices[2][0]*(vertices[0][1]-vertices[1][1]))

if __name__ == '__main__':
    main = Main()
    main.main_loop()