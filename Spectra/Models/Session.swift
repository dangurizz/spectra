import Foundation

struct Session: Identifiable, Codable {
    let id: UUID
    let spotId: UUID
    let startTime: Date
    let endTime: Date
    let rating: Double
    let notes: String?
    let conditions: Conditions?
}
