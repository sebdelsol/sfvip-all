from build_config import Build, Github
from builder import Builder, Template, create_logo, get_args

if __name__ == "__main__":
    args = get_args()
    builder = Builder(args, Build)
    builder.build_all()
    template = Template(Build, Github)
    template.create_readme()
    template.create_post()
    create_logo(Build.Logo)
