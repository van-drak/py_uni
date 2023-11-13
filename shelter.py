import datetime


class Shelter:
    def __init__(self):
        self.animals = []
        self.foster_parents = []

    def add_animal(self, **kwargs):
        animal = Animal(**kwargs)
        self.animals.append(animal)
        return animal

    def list_animals(self, **kwargs):
        list_of_animals = []
        for animal in self.animals:
            addable = True
            if animal.adopted is not None and animal.adopted.date < kwargs["date"] or animal.date_of_entry > kwargs["date"]:
                continue

            if animal.foster is not None:
                _, d = animal.foster
                if d < kwargs["date"]:
                    addable = False
                    continue

            for key in kwargs:
                if key == "date":
                    continue
                if animal.get_attribute(key) != kwargs[key]:
                    addable = False
                    break
            if not addable:
                continue

            for foster_care in animal.fosters:
                _, start, end = foster_care
                if start < kwargs["date"] < end:
                    addable = False
                    break
            if not addable:
                continue

            list_of_animals.append(animal)

        return list_of_animals

    def add_foster_parent(self, **kwargs):
        self.foster_parents.append(FosterParent(**kwargs))

    def available_foster_parents(self, date):
        res = []
        for parent in self.foster_parents:
            if parent.available(date):
                res.append(parent)

        return res


def exam_compare(date, start, end):
    if start is None and end is None:
        return True
    if start is None:
        return date <= end
    if end is None:
        return start <= date
    return start <= date <= end


class Animal:
    def __init__(self, **kwargs):
        if len(kwargs) != 6:
            raise RuntimeError("Invalid number of arguments")

        self.name = kwargs["name"]
        self.year_of_birth = kwargs["year_of_birth"]
        self.gender = kwargs["gender"]
        self.date_of_entry = kwargs["date_of_entry"]
        self.species = kwargs["species"]
        self.breed = kwargs["breed"]
        self.exams = []
        self.adopted = None
        self.foster = None
        self.fosters = []  # (parent, start, end)

    def __eq__(self, other):
        if self.name == other.name and self.year_of_birth == other.year_of_birth and self.gender == other.gender and self.species == other.species and self.breed == other.breed and self.date_of_entry == other.date_of_entry:
            return True
        return False

    def add_exam(self, **kwargs):
        if self.adopted is not None and kwargs["date"] > self.adopted.date:
            raise RuntimeError("Animal was already adopted")

        if self.foster is not None:
            p, d = self.foster
            if kwargs["date"] > d:
                raise RuntimeError(
                    "First you have to end foster care from ", d, " by ", p)

        for _, start, end in self.fosters:
            if start < kwargs["date"] < end:
                raise RuntimeError(
                    "Animal was in foster care during this time")

        if kwargs["date"] < self.date_of_entry or datetime.date(self.year_of_birth, 1, 1) > kwargs["date"]:
            raise RuntimeError("Animal was not in shelter at specific time")

        self.exams.append(Exam(**kwargs))

    def list_exams(self, **kwargs):
        res = []
        if kwargs["start"] is not None and kwargs["end"] is not None and kwargs["start"] > kwargs["end"]:
            raise RuntimeError("Date END can not be older than date START")

        for exam in self.exams:
            if exam_compare(exam.date, kwargs["start"], kwargs["end"]):
                res.append(exam)

        return res

    def adopt(self, **kwargs):
        if self.adopted is not None:
            raise RuntimeError("Animal is already adopted")

        if self.date_of_entry > kwargs["date"]:
            raise RuntimeError("Animal was not in shelter at specific time")

        for _, start, end in self.fosters:
            if start <= kwargs["date"] < end:
                raise RuntimeError(
                    "Animal can not be adopted during foster care")

        if self.foster is not None:
            _, start = self.foster
            if kwargs["date"] >= start:
                raise RuntimeError(
                    "Animal was in foster care at specific time")

        self.adopted = Adoption(**kwargs)

    def start_foster(self, date, parent):
        if self.adopted is not None and self.adopted.date < date:
            raise RuntimeError("Animal was adopted in given time")

        if self.foster is not None:
            p, d = self.foster
            raise RuntimeError("First end foster started in ", d, "by ", p)

        for _, start, end in self.fosters:
            if start < date < end:
                raise RuntimeError("Animal is in foster care already")

        if not parent.available(date):
            raise RuntimeError(
                "Parent is not available to take care of more animals")

        self.foster = ((parent, date))
        parent.actual_foster.append((self, date))

    def end_foster(self, date):
        if self.foster == None:
            raise RuntimeError("Animal is not in foster care yet")

        if self.adopted is not None and self.adopted.date < date:
            raise RuntimeError("Animal was adopted in given time")

        p, d = self.foster
        if d > date:
            raise RuntimeError("Foster can not end earlier than it started")

        self.fosters.append((p, d, date))
        p.dates.append((d, date))
        _, foster_start = self.foster
        p.actual_foster.remove((self, foster_start))
        self.foster = None

    def get_attribute(self, attribute):
        attributes = {"name": self.name, "year_of_birth": self.year_of_birth, "gender": self.gender,
                      "date_of_entry": self.date_of_entry, "species": self.species, "breed": self.breed,
                      "exams": self.exams, "adoption": self.adopted}
        return attributes[attribute]


class Exam:
    def __init__(self, vet, date, report):
        self.vet = vet
        self.date = date
        self.report = report


class FosterParent:
    def __init__(self, **kwargs):
        if len(kwargs) != 4:
            raise RuntimeError("Invalid number of arguments")

        self.name = kwargs["name"]
        self.address = kwargs["address"]
        self.phone = kwargs["phone_number"]
        self.max_animals = kwargs["max_animals"]
        self.actual_foster = []
        self.dates = []

    def available(self, date):
        count = 0
        for start, end in self.dates:
            if start <= date <= end:
                count += 1

        for _, start_date in self.actual_foster:
            if start_date < date:
                count += 1

        return count < self.max_animals


class Adoption:
    def __init__(self, date, adopter_name, adopter_address):
        self.date = date
        self.adopter_name = adopter_name
        self.adopter_address = adopter_address
