"""empty message

Revision ID: f33e63753166
Revises: 
Create Date: 2023-07-23 13:23:03.953111

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f33e63753166'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('users',
        sa.Column('username', sa.String(length=40), nullable=True),
        sa.Column('email', sa.String(length=40), nullable=True),
        sa.Column('password', sa.String(length=100), nullable=True),
        sa.Column('last_login', sa.String(length=50), nullable=True),
        sa.Column('joined', sa.String(length=50), nullable=True),
        sa.Column('is_stuff', sa.Boolean(), nullable=True),
        sa.Column('is_superuser', sa.Boolean(), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('username')
    )
    op.create_table('sciences',
        sa.Column('title', sa.String(length=40), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=100), nullable=True),
        sa.Column('slug', sa.String(length=40), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('title')
    )
    op.create_table('categories',
        sa.Column('title', sa.String(length=40), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=100), nullable=True),
        sa.Column('science_id', sa.String(length=100), nullable=True),
        sa.Column('slug', sa.String(length=40), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['science_id'], ['sciences.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('title')
    )
    op.create_table('formulas',
        sa.Column('title', sa.String(length=40), nullable=True),
        sa.Column('formula', sa.String(length=40), nullable=True),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('image_path', sa.String(length=100), nullable=True),
        sa.Column('category_id', sa.String(length=100), nullable=True),
        sa.Column('slug', sa.String(length=40), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['category_id'], ['categories.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('slug'),
        sa.UniqueConstraint('title')
    )
    op.create_table('problems',
        sa.Column('title', sa.String(length=100), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('time_asked', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('time_answered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_solved', sa.Boolean(), nullable=True),
        # sa.Column('solution_id', sa.String(length=100), nullable=True),
        sa.Column('science_id', sa.String(length=100), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['science_id'], ['sciences.id'], ondelete='CASCADE'),
        # sa.ForeignKeyConstraint(['solution_id'], ['solutions.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('problemmedias',
        sa.Column('problem_id', sa.String(length=100), nullable=True),
        sa.Column('media_path', sa.String(length=255), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('solutions',
        sa.Column('author_id', sa.String(length=100), nullable=True),
        sa.Column('problem_id', sa.String(length=100), nullable=True),
        sa.Column('text', sa.Text(), nullable=True),
        sa.Column('time_created', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['author_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('solutionmedias',
        sa.Column('solution_id', sa.String(length=100), nullable=True),
        sa.Column('media_path', sa.String(length=255), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['solution_id'], ['solutions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_table('history',
        sa.Column('formula_id', sa.String(length=100), nullable=True),
        sa.Column('result', sa.String(length=100), nullable=True),
        sa.Column('formula_url', sa.String(length=50), nullable=True),
        sa.Column('date_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('user_id', sa.String(length=100), nullable=True),
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.ForeignKeyConstraint(['formula_id'], ['formulas.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.add_column(
        'problems',
        sa.Column("solution_id", sa.String(200), nullable=True)
    )

    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('history')
    op.drop_table('formulas')
    op.drop_table('solutionmedias')
    op.drop_table('problemmedias')
    op.drop_table('categories')
    op.drop_table('users')
    op.drop_table('solutions')
    op.drop_table('sciences')
    op.drop_table('problems')
    # ### end Alembic commands ###
