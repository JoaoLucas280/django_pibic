from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction

from aluno.models import Enrollment, Student

from curso.models import Course, Discipline, Semester


DISCIPLINES = {
    "MET101": ("Metodologia Científica", 60),
    "COM101": ("Comunicação e Expressão", 60),
    "INF101": ("Informática Aplicada", 60),
    "EST101": ("Estatística Aplicada", 60),
    "ADM101": ("Fundamentos de Administração", 60),
    "ECO101": ("Economia", 60),
    "CON101": ("Contabilidade Geral", 60),
    "FIN101": ("Gestão Financeira", 60),
    "MKT101": ("Marketing", 60),
    "RH101": ("Gestão de Pessoas", 60),
    "EMP101": ("Empreendedorismo", 60),
    "ALG101": ("Algoritmos e Programação", 80),
    "LOG101": ("Lógica de Programação", 60),
    "MAT101": ("Matemática Discreta", 60),
    "MAT102": ("Cálculo Aplicado", 80),
    "BD101": ("Banco de Dados", 80),
    "WEB101": ("Desenvolvimento Web", 80),
    "ENG101": ("Engenharia de Software", 80),
    "RED101": ("Redes de Computadores", 60),
    "SO101": ("Sistemas Operacionais", 60),
    "SEG101": ("Segurança da Informação", 60),
    "IA101": ("Inteligência Artificial", 60),
    "UX101": ("Interação Humano-Computador", 60),
    "DIR101": ("Introdução ao Direito", 60),
    "CIV101": ("Direito Civil", 80),
    "PEN101": ("Direito Penal", 80),
    "PUB101": ("Direito Público", 60),
    "SOC101": ("Sociologia", 60),
    "BIO101": ("Biologia Geral", 60),
    "ANA101": ("Anatomia Humana", 80),
    "FIS101": ("Fisiologia Humana", 80),
    "SAU101": ("Saúde Coletiva", 60),
    "ENF101": ("Fundamentos de Enfermagem", 80),
    "FAR101": ("Farmacologia", 60),
    "EPI101": ("Epidemiologia", 60),
    "CIN101": ("Cinesiologia", 80),
    "REAB101": ("Recursos Terapêuticos", 80),
    "PSI101": ("Psicologia Geral", 60),
    "PSI102": ("Psicologia do Desenvolvimento", 80),
    "PED101": ("Educação e Aprendizagem", 60),
    "DID101": ("Didática", 60),
    "HIS101": ("História da Educação", 60),
    "ENG102": ("Desenho Técnico", 80),
    "MEC101": ("Mecânica dos Materiais", 80),
    "EST102": ("Estruturas de Concreto", 80),
    "DES101": ("Fundamentos do Design", 60),
    "ETI101": ("Ética Profissional", 60),
    "PROC101": ("Processo Civil", 80),
    "ORG101": ("Organização de Serviços de Saúde", 60),
}


CURRICULA = {
    "Administração": (
        ("ADM101", "ECO101", "MET101"),
        ("CON101", "COM101", "EST101"),
        ("FIN101", "ADM101", "MAT101"),
        ("MKT101", "RH101", "COM101"),
        ("ECO101", "FIN101", "EST101"),
        ("EMP101", "MKT101", "ADM101"),
        ("RH101", "FIN101", "MET101"),
        ("EMP101", "CON101", "MKT101"),
    ),
    "Análise e Desenvolvimento de Sistemas": (
        ("ALG101", "LOG101", "INF101"),
        ("BD101", "MAT101", "MET101"),
        ("WEB101", "UX101", "COM101"),
        ("SO101", "RED101", "EST101"),
        ("ENG101", "BD101", "ALG101"),
        ("SEG101", "SO101", "RED101"),
        ("IA101", "EST101", "ALG101"),
        ("EMP101", "MET101", "WEB101"),
    ),
    "Ciência da Computação": (
        ("MAT101", "ALG101", "MET101"),
        ("LOG101", "INF101", "EST101"),
        ("BD101", "SO101", "MAT102"),
        ("RED101", "ENG101", "COM101"),
        ("IA101", "ALG101", "EST101"),
        ("SEG101", "BD101", "SO101"),
        ("WEB101", "UX101", "ENG101"),
        ("EMP101", "MET101", "IA101"),
    ),
    "Ciências Contábeis": (
        ("CON101", "ADM101", "MET101"),
        ("ECO101", "MAT101", "COM101"),
        ("FIN101", "EST101", "CON101"),
        ("DIR101", "PUB101", "ADM101"),
        ("ECO101", "FIN101", "EST101"),
        ("EMP101", "CON101", "ETI101"),
        ("RH101", "MKT101", "MET101"),
        ("FIN101", "CON101", "EMP101"),
    ),
    "Direito": (
        ("DIR101", "SOC101", "MET101"),
        ("CIV101", "PUB101", "COM101"),
        ("PEN101", "ETI101", "DIR101"),
        ("PROC101", "CIV101", "SOC101"),
        ("PUB101", "PEN101", "MET101"),
        ("PROC101", "ETI101", "COM101"),
        ("CIV101", "DIR101", "EMP101"),
        ("PROC101", "PUB101", "PEN101"),
    ),
    "Enfermagem": (
        ("BIO101", "ANA101", "MET101"),
        ("FIS101", "SAU101", "COM101"),
        ("ENF101", "EPI101", "BIO101"),
        ("FAR101", "ANA101", "ORG101"),
        ("ENF101", "FIS101", "EPI101"),
        ("SAU101", "FAR101", "ETI101"),
        ("ORG101", "ENF101", "MET101"),
        ("EPI101", "SAU101", "ETI101"),
    ),
    "Engenharia Civil": (
        ("MAT102", "ENG102", "MET101"),
        ("MEC101", "MAT101", "COM101"),
        ("EST102", "MAT102", "FIS101"),
        ("ENG102", "MEC101", "EST101"),
        ("EST102", "MAT102", "ETI101"),
        ("ENG102", "MEC101", "ECO101"),
        ("EST102", "EMP101", "MET101"),
        ("MEC101", "EST102", "ETI101"),
    ),
    "Engenharia de Software": (
        ("ALG101", "LOG101", "MET101"),
        ("MAT101", "BD101", "INF101"),
        ("ENG101", "WEB101", "COM101"),
        ("SO101", "RED101", "EST101"),
        ("UX101", "SEG101", "BD101"),
        ("IA101", "ENG101", "ALG101"),
        ("WEB101", "EMP101", "ETI101"),
        ("SEG101", "IA101", "MET101"),
    ),
    "Fisioterapia": (
        ("BIO101", "ANA101", "MET101"),
        ("FIS101", "CIN101", "COM101"),
        ("REAB101", "PSI101", "BIO101"),
        ("EPI101", "SAU101", "FIS101"),
        ("CIN101", "REAB101", "ETI101"),
        ("ANA101", "PSI102", "ORG101"),
        ("REAB101", "SAU101", "MET101"),
        ("CIN101", "PSI102", "ETI101"),
    ),
    "Pedagogia": (
        ("PED101", "HIS101", "MET101"),
        ("PSI102", "SOC101", "COM101"),
        ("DID101", "PED101", "PSI101"),
        ("HIS101", "SOC101", "ETI101"),
        ("DID101", "PSI102", "COM101"),
        ("PED101", "EMP101", "MET101"),
        ("PSI101", "DID101", "ETI101"),
        ("HIS101", "PSI102", "PED101"),
    ),
    "Psicologia": (
        ("PSI101", "BIO101", "MET101"),
        ("PSI102", "SOC101", "COM101"),
        ("EST101", "FIS101", "PSI101"),
        ("ETI101", "PSI102", "BIO101"),
        ("SAU101", "EPI101", "EST101"),
        ("PSI101", "PSI102", "MET101"),
        ("SOC101", "ETI101", "ORG101"),
        ("EPI101", "SAU101", "PSI102"),
    ),
    "Sistemas de Informação": (
        ("ALG101", "ADM101", "MET101"),
        ("BD101", "MAT101", "COM101"),
        ("WEB101", "ENG101", "EST101"),
        ("SO101", "RED101", "ADM101"),
        ("SEG101", "BD101", "FIN101"),
        ("IA101", "UX101", "EST101"),
        ("ENG101", "EMP101", "MET101"),
        ("WEB101", "SEG101", "ETI101"),
    ),
}


FIRST_NAMES = ("Ana Beatriz", "Bruno Henrique", "Camila", "Diego", "Eduarda")
LAST_NAMES = ("Silva", "Oliveira", "Santos", "Costa", "Almeida", "Souza")


class Command(BaseCommand):
    help = "Adiciona dados acadêmicos de demonstração sem apagar registros existentes."

    @transaction.atomic
    def handle(self, *args, **options):
        created_courses = 0
        created_disciplines = 0
        created_semesters = 0
        created_students = 0
        created_enrollments = 0
        disciplines = {}

        for code, (name, class_load) in DISCIPLINES.items():
            discipline = Discipline.objects.filter(code=code).order_by("pk").first()
            if discipline is None:
                discipline = Discipline.objects.create(
                    name=name,
                    code=code,
                    class_load=class_load,
                )
                created_disciplines += 1
            disciplines[code] = discipline

        for course_index, (course_name, terms) in enumerate(CURRICULA.items(), start=1):
            course, was_created = Course.objects.get_or_create(
                name=course_name,
                defaults={"duration_semesters": len(terms)},
            )
            created_courses += was_created

            for semester_number, discipline_codes in enumerate(terms, start=1):
                semester, was_created = Semester.objects.get_or_create(
                    course=course,
                    number=semester_number,
                )
                created_semesters += was_created
                semester.disciplines.add(
                    *(disciplines[code] for code in discipline_codes)
                )

            for student_number in range(1, 5):
                name_index = (course_index + student_number - 2) % len(FIRST_NAMES)
                first_name = FIRST_NAMES[name_index]
                last_name = LAST_NAMES[
                    (course_index + student_number - 2) % len(LAST_NAMES)
                ]
                student, was_created = Student.objects.get_or_create(
                    email=f"demo.aluno{course_index:02d}.{student_number:02d}@example.com",
                    defaults={
                        "name": f"{first_name} {last_name}",
                        "rgm": f"{course_index:02d}{student_number:05d}",
                        "course": course,
                    },
                )
                created_students += was_created
                created_enrollments += self.enroll_demo_student(student, course)

        self.stdout.write(
            self.style.SUCCESS(
                "Dados de demonstração prontos. "
                f"Criados nesta execução: {created_courses} cursos, "
                f"{created_disciplines} disciplinas, {created_semesters} semestres, "
                f"{created_students} alunos, {created_enrollments} matrículas."
            )
        )

    def enroll_demo_student(self, student, course):
        """1º semestre já avaliado (com aprovações e reprovações); 2º semestre em andamento."""
        created = 0
        for semester in course.semesters.filter(number__lte=2).prefetch_related("disciplines"):
            for discipline in semester.disciplines.all():
                defaults = {}
                if semester.number == 1:
                    seed = student.pk * 7 + discipline.pk * 3  # determinístico: mesma nota a cada execução
                    defaults = {
                        "grade": Decimal(4) + Decimal(seed % 61) / 10,  # 4,0 a 10,0
                        "attendance": 70 + seed % 31,  # 70% a 100%: poucas reprovações por falta
                    }
                _, was_created = Enrollment.objects.get_or_create(
                    student=student, discipline=discipline, defaults=defaults
                )
                created += was_created
        return created
