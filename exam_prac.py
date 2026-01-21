"""
Вам необходимо реализовать систему управления бронированием номеров в отеле (Hotel Booking System),
которая поддерживает различные типы операций: AddRoom (добавление номера), RegisterGuest (регистрация гостя),
CreateBooking (создание бронирования), CancelBooking (отмена бронирования), CheckIn (заезд) и CheckOut (выезд).

Каждая операция должна:
    Иметь метод execute(hotel: Hotel).
    Менять состояние системы отеля.
    Могла быть отменена (метод undo).

Все изменения состояния системы отеля должны происходить только через эти операции.

В этой реализации:
    Hotel хранит комнаты, гостей и бронирования, а также историю операций (для undo_last()).
    Room, Guest, Booking — простые структуры данных.
    Operation — абстрактный базовый класс (ABC) для всех операций.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date
from typing import Dict, List, Optional


@dataclass
class Room:
    number: int
    capacity: int
    price_per_night: int


@dataclass
class Guest:
    guest_id: int
    name: str


@dataclass
class Booking:
    booking_id: int
    guest_id: int
    room_number: int
    check_in_date: date
    check_out_date: date
    status: str


class Hotel:
    def __init__(self) -> None:
        self.rooms: Dict[int, Room] = {}
        self.guests: Dict[int, Guest] = {}
        self.bookings: Dict[int, Booking] = {}

        self._next_guest_id: int = 1
        self._next_booking_id: int = 1

        self.history: List[Operation] = []

    def apply(self, operation: "Operation") -> None:
        operation.execute(self)
        self.history.append(operation)

    def undo_last(self) -> None:
        if not self.history:
            raise ValueError("Нет операций для отмены.")
        operation = self.history.pop()
        operation.undo(self)


class Operation(ABC):
    @abstractmethod
    def execute(self, hotel: Hotel) -> None:
        pass

    @abstractmethod
    def undo(self, hotel: Hotel) -> None:
        pass


class AddRoom(Operation):
    def __init__(self, number: int, capacity: int, price_per_night: int) -> None:
        self.number = number
        self.capacity = capacity
        self.price_per_night = price_per_night
        self._added = False

    def execute(self, hotel: Hotel) -> None:
        if self.number in hotel.rooms:
            raise ValueError("Номер с таким номером уже номер(уже существует).")
        hotel.rooms[self.number] = Room(self.number, self.capacity, self.price_per_night)
        self._added = True

    def undo(self, hotel: Hotel) -> None:
        if self._added and self.number in hotel.rooms:
            del hotel.rooms[self.number]


class RegisterGuest(Operation):
    def __init__(self, name: str) -> None:
        self.name = name
        self.guest_id: Optional[int] = None

    def execute(self, hotel: Hotel) -> None:
        self.guest_id = hotel._next_guest_id
        hotel._next_guest_id += 1
        hotel.guests[self.guest_id] = Guest(self.guest_id, self.name)

    def undo(self, hotel: Hotel) -> None:
        if self.guest_id is not None and self.guest_id in hotel.guests:
            del hotel.guests[self.guest_id]


class CreateBooking(Operation):
    def __init__(self, guest_id: int, room_number: int, check_in_date: date, check_out_date: date) -> None:
        self.guest_id = guest_id
        self.room_number = room_number
        self.check_in_date = check_in_date
        self.check_out_date = check_out_date
        self.booking_id: Optional[int] = None

    def execute(self, hotel: Hotel) -> None:
        if self.guest_id not in hotel.guests:
            raise ValueError("Гость не зарегистрирован.")
        if self.room_number not in hotel.rooms:
            raise ValueError("Такого номера нет.")
        if self.check_in_date >= self.check_out_date:
            raise ValueError("Дата выезда должна быть позже даты заезда.")
        if not self._room_is_available(hotel):
            raise ValueError("Номер недоступен на выбранные даты.")

        self.booking_id = hotel._next_booking_id
        hotel._next_booking_id += 1

        hotel.bookings[self.booking_id] = Booking(
            booking_id=self.booking_id,
            guest_id=self.guest_id,
            room_number=self.room_number,
            check_in_date=self.check_in_date,
            check_out_date=self.check_out_date,
            status="booked",
        )

    def undo(self, hotel: Hotel) -> None:
        if self.booking_id is not None and self.booking_id in hotel.bookings:
            del hotel.bookings[self.booking_id]

    def _room_is_available(self, hotel: Hotel) -> bool:
        for booking in hotel.bookings.values():
            if booking.room_number != self.room_number:
                continue
            if booking.status in ("cancelled", "checked_out"):
                continue
            if self._dates_overlap(self.check_in_date, self.check_out_date, booking.check_in_date, booking.check_out_date):
                return False
        return True

    @staticmethod
    def _dates_overlap(a_start: date, a_end: date, b_start: date, b_end: date) -> bool:
        return a_start < b_end and b_start < a_end


class CancelBooking(Operation):
    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        self._prev_status: Optional[str] = None

    def execute(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            raise ValueError("Бронирование не найдено.")
        if booking.status == "checked_out":
            raise ValueError("Нельзя отменить: гость уже выехал.")
        if booking.status == "cancelled":
            raise ValueError("Бронирование уже отменено.")

        self._prev_status = booking.status
        booking.status = "cancelled"

    def undo(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            return
        if self._prev_status is not None:
            booking.status = self._prev_status


class CheckIn(Operation):
    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        self._prev_status: Optional[str] = None

    def execute(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            raise ValueError("Бронирование не найдено.")
        if booking.status != "booked":
            raise ValueError("Заезд возможен только для статуса 'booked'.")

        self._prev_status = booking.status
        booking.status = "checked_in"

    def undo(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            return
        if self._prev_status is not None:
            booking.status = self._prev_status


class CheckOut(Operation):
    def __init__(self, booking_id: int) -> None:
        self.booking_id = booking_id
        self._prev_status: Optional[str] = None

    def execute(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            raise ValueError("Бронирование не найдено.")
        if booking.status != "checked_in":
            raise ValueError("Выезд возможен только для статуса 'checked_in'.")

        self._prev_status = booking.status
        booking.status = "checked_out"

    def undo(self, hotel: Hotel) -> None:
        booking = hotel.bookings.get(self.booking_id)
        if booking is None:
            return
        if self._prev_status is not None:
            booking.status = self._prev_status


if __name__ == "__main__":
    hotel = Hotel()

    hotel.apply(AddRoom(number=101, capacity=2, price_per_night=3500))
    hotel.apply(AddRoom(number=102, capacity=3, price_per_night=4500))

    op_guest = RegisterGuest(name="Некий Гость")
    hotel.apply(op_guest)
    guest_id = op_guest.guest_id

    op_booking = CreateBooking(
        guest_id=guest_id,
        room_number=101,
        check_in_date=date(2026, 1, 25),
        check_out_date=date(2026, 1, 28),
    )
    hotel.apply(op_booking)
    booking_id = op_booking.booking_id

    print("Комнаты:", hotel.rooms)
    print("Гости:", hotel.guests)
    print("Бронирования:", hotel.bookings)
    print(' ')
    hotel.apply(CheckIn(booking_id=booking_id))
    print("После заезда:", hotel.bookings[booking_id])
    print(' ')
    hotel.apply(CheckOut(booking_id=booking_id))
    print("После выезда:", hotel.bookings[booking_id])
    print(' ')
    hotel.undo_last()
    print("Отменили последний шаг (выезд):", hotel.bookings[booking_id])
    print(' ')
    hotel.apply(CancelBooking(booking_id=booking_id))
    print("После отмены бронирования:", hotel.bookings[booking_id])
    print(' ')
    hotel.undo_last()
    print("Отменили отмену бронирования:", hotel.bookings[booking_id])
